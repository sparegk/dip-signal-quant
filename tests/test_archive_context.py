"""Decision context cannot rewrite, backdate or inject future outcomes."""

from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import archive_context as context
from src import paper_archive as archive
from src.data import PROVENANCE_KEY, save_parquet
from src.preservation import read_record


@pytest.fixture
def sealed(tmp_path, monkeypatch):
    config=archive.load_protocol(); config["universe"]=["ABT","BMY"]
    monkeypatch.setattr(archive,"load_protocol",lambda:deepcopy(config))
    frames={}; dates=pd.bdate_range(end="2026-10-01",periods=300).astype("datetime64[ns]")
    for ticker in ["ABT","BMY","SPY"]:
        prices=100+np.arange(300)*.03+np.sin(np.arange(300)/5)
        frame=pd.DataFrame(dict(timestamp=dates,ticker=ticker,open=prices,high=prices+1,
                                low=prices-1,close=prices,volume=np.full(300,100,dtype=np.int64)))
        frame.attrs[PROVENANCE_KEY]=dict(schema_version=1,provider="yfinance",ticker=ticker,interval="1d",
             retrieved_at="2026-10-02T11:00:00+00:00",requested_start="2016-09-29",requested_end="2026-10-02",
             adjustment="auto_adjust=True; provider-reported volume")
        save_parquet(frame,tmp_path/"cache"/(ticker+".parquet")); frames[ticker]=frame
    root=tmp_path/"archive"
    inputs={t:archive.capture_input(root,t,config=config,session="2026-10-01",replay_cache=tmp_path/"cache") for t in frames}
    for item in inputs.values(): item["input_kind"]="new_provider_vintage"
    intent=archive.begin_run(root,"test",session="2026-10-01",mode="collect",config=config,
                            code={"revision":"test","dirty":False},clock=lambda:"2026-10-02T10:00:00Z")
    times=iter(["2026-10-02T12:00:00Z","2026-10-02T12:00:01Z"])
    archive.finish_run(root,intent,inputs,clock=lambda:next(times))
    monkeypatch.setattr(context,"code_identity",lambda:{"revision":"test","dirty":False,"source_sha256":{}})
    return root,frames,config


def test_context_is_append_only_and_separate_from_original_decisions(sealed):
    root,_,_=sealed
    before=(root/"runs/test/result.json").read_bytes()
    times=iter(["2026-10-02T12:10:00Z","2026-10-02T12:10:01Z"])
    first=context.preserve_context(root,"test",clock=lambda:next(times))
    assert context.preserve_context(root,"test",clock=lambda:pytest.fail("Retry must not backdate"))==first
    assert (root/"runs/test/result.json").read_bytes()==before
    receipt=read_record(root/"context_receipts/test.json")
    assert set(receipt["classifications"].values())=={"prospective_context"}
    assert all(r["context"]["candidate_exit_policies"]==[] for r in first["records"])


def test_late_context_cannot_become_prospective(sealed):
    root,_,_=sealed
    context.preserve_context(root,"test",clock=lambda:"2026-10-02T15:00:00Z")
    assert set(read_record(root/"context_receipts/test.json")["classifications"].values())=={"retrospective_context"}


def test_future_rows_cannot_change_context(sealed):
    _,frames,config=sealed
    rules=json.loads((context.ROOT/"config/archive_context.json").read_bytes())
    one=context.signal_context(frames["ABT"],frames["SPY"],"2026-09-25",config["signal_parameters"],rules)
    stock=frames["ABT"].copy(); spy=frames["SPY"].copy()
    for f in [stock,spy]: f.loc[f.timestamp.gt(pd.Timestamp("2026-09-25")),["open","high","low","close"]]*=10
    assert context.signal_context(stock,spy,"2026-09-25",config["signal_parameters"],rules)==one


def test_future_fields_fail_validation_and_altered_bytes_fail_integrity(sealed):
    root,_,_=sealed
    result=context.preserve_context(root,"test",clock=lambda:"2026-10-02T15:00:00Z")
    changed=deepcopy(result);changed["records"][0]["context"]["future_return"]=1.
    with pytest.raises(ValueError,match="future context"): context.validate_context(changed)
    p=root/"contexts/test.json";p.write_bytes(p.read_bytes().replace(b'"volume":100.0',b'"volume":200.0'))
    with pytest.raises(ValueError,match="hash mismatch"): context.preserve_context(root,"test")


def test_interrupted_seal_recovery_cannot_promote_context(sealed):
    root,_,_=sealed
    original=context.preserve_context(root,"test",clock=lambda:"2026-10-02T12:10:00Z")
    (root/"context_receipts/test.json").unlink()
    assert context.preserve_context(root,"test",clock=lambda:"2026-10-02T12:20:00Z")==original
    assert set(read_record(root/"context_receipts/test.json")["classifications"].values())=={"unverifiable_context"}


def test_context_timestamp_cannot_predate_original_decision(sealed):
    root,_,_=sealed
    with pytest.raises(ValueError,match="predates original"):
        context.preserve_context(root,"test",clock=lambda:"2026-10-02T10:00:00Z")
    assert not (root/"contexts/test.json").exists()


def test_read_context_verifies_seal_and_input_linkage(sealed):
    root,_,_=sealed
    assert context.read_context(root,"test") is None
    result=context.preserve_context(root,"test",clock=lambda:"2026-10-02T12:10:00Z")
    assert context.read_context(root,"test")["payload"]==result
    assert set(context.read_context(root,"test")["classifications"].values())=={"prospective_context"}
