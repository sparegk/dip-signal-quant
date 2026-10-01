from copy import deepcopy

import numpy as np
import pandas as pd
import pytest

from src.data import PROVENANCE_KEY, clean_data
from src.data_audit import audit_ohlc, preserve_raw, restore_raw
from src.preservation import digest, get_object, publish, put_object, read_record, write_record


@pytest.fixture
def raw():
    frame = pd.DataFrame({"Open": [10., 10.], "High": [11., 11.], "Low": [9., 9.],
                          "Close": [10., 10.], "Volume": [100, 200]},
                         index=pd.DatetimeIndex(["2026-09-25", "2026-09-28"], name="Date"))
    frame.attrs[PROVENANCE_KEY] = {"retrieved_at": "2026-09-30T21:00:00+00:00"}
    return frame


@pytest.mark.parametrize("field,value,rule,gap", [
    ("Open", 8., "open_lt_low", 1.), ("Open", 12., "open_gt_high", 1.),
    ("Close", 8., "close_lt_low", 1.), ("Close", 12., "close_gt_high", 1.),
    ("Low", 12., "low_gt_high", 1.)])
def test_exact_discrepancies_without_repair(raw, field, value, rule, gap):
    raw.loc[raw.index[0], field] = value
    before = deepcopy(raw)
    summary, details = audit_ohlc(raw, "ABT", vintage="new_diagnostic")
    assert summary["affected_rows"] == 1 and summary["affected_fraction"] == .5
    row = details.loc[details.rule == rule].iloc[0]
    assert row.absolute_gap == gap
    assert row.relative_gap > 0 and row.spacing_units > 0
    pd.testing.assert_frame_equal(raw, before)
    with pytest.raises(ValueError, match="Malformed OHLC"):
        clean_data(raw, "ABT")


def test_one_ulp_is_reported_and_remains_strictly_rejected(raw):
    raw.loc[raw.index[0], "Close"] = np.nextafter(11., np.inf)
    summary, details = audit_ohlc(raw, "ABT", vintage="new_diagnostic")
    assert details.spacing_units.iloc[0] == 1
    assert summary["validation_error"].startswith("Malformed OHLC")


@pytest.mark.parametrize("value", [np.nan, np.inf, -1., 0.])
def test_invalid_numeric_rows_are_retained(raw, value):
    raw.loc[raw.index[0], "Open"] = value
    summary, details = audit_ohlc(raw, "ABT", vintage="new_diagnostic")
    assert "invalid_open" in set(details.rule)
    assert summary["rows"] == 2 and summary["affected_rows"] == 1


def test_raw_rejection_and_vintage_preservation(raw, tmp_path):
    raw.loc[raw.index[0], "Close"] = 12.
    snapshot = preserve_raw(tmp_path, raw)
    restored = restore_raw(tmp_path, snapshot)
    pd.testing.assert_frame_equal(raw, restored)
    assert restored.attrs == raw.attrs
    assert snapshot == preserve_raw(tmp_path, raw)
    first, _ = audit_ohlc(restored, "ABT", vintage="original_rejected")
    second, _ = audit_ohlc(restored, "ABT", vintage="new_diagnostic")
    assert first["vintage"] != second["vintage"]
    raw.attrs[PROVENANCE_KEY]["retrieved_at"] = "2026-10-01T21:00:00+00:00"
    assert preserve_raw(tmp_path, raw)["raw_sha256"] != snapshot["raw_sha256"]


def test_schema_failure_is_not_silently_normalized(raw):
    summary, details = audit_ohlc(raw.reset_index(drop=True), "ABT", vintage="new_diagnostic")
    assert summary["diagnostic_status"] == "unsupported_schema" and details.empty


def test_good_rows_have_zero_affected_fraction(raw):
    summary, details = audit_ohlc(raw, "ABT", vintage="new_diagnostic")
    assert summary["validation_error"] is None and summary["affected_fraction"] == 0
    assert details.empty and summary["max_absolute_gap"] is None


def test_object_and_record_hashes_detect_tampering(tmp_path):
    key = put_object(tmp_path, b"input")
    assert get_object(tmp_path, key) == b"input"
    (tmp_path / "objects" / key).write_bytes(b"changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        get_object(tmp_path, key)
    path = tmp_path / "record.json"
    assert write_record(path, {"a": 1})
    assert not write_record(path, {"a": 1})
    with pytest.raises(ValueError, match="Conflicting"):
        write_record(path, {"a": 2})
    path.write_bytes(path.read_bytes().replace(b'"a":1', b'"a":2'))
    with pytest.raises(ValueError, match="hash mismatch"):
        read_record(path)


def test_interrupted_publish_does_not_expose_partial_record(tmp_path, monkeypatch):
    path = tmp_path / "record.json"
    def fail(*args):
        raise OSError("interrupted")
    with monkeypatch.context() as patch:
        patch.setattr("src.preservation.os.link", fail)
        with pytest.raises(OSError):
            publish(path, b"whole")
    assert not path.exists()
    publish(path, b"whole")
    assert digest(path.read_bytes()) == digest(b"whole")


def test_audit_runner_offline_replay_and_failure_records(raw, tmp_path, monkeypatch):
    from scripts import audit_exp003 as runner
    from pathlib import Path
    import json
    project = tmp_path / "project"
    (project / "config").mkdir(parents=True)
    (project / "data/market").mkdir(parents=True)
    (project / "config/exp003.json").write_text(json.dumps({"audit_tickers": ["ABT", "BMY"],
        "audit_start": "2026-09-01", "audit_end_exclusive": "2026-09-29"}))
    (project / "data/market/exp002-acquisition.json").write_text(json.dumps({"exclusions": [
        {"ticker": t, "detail": "Malformed OHLC"} for t in ["ABT", "BMY"]]}))
    monkeypatch.setattr(runner, "ROOT", project)
    def download(ticker, **kwargs):
        if ticker == "BMY":
            raise RuntimeError("network failure")
        return raw
    monkeypatch.setattr(runner, "download_raw_data", download)
    root = tmp_path / "quarantine"
    first = runner.run_audit(root, download=True)
    monkeypatch.setattr(runner, "download_raw_data", lambda *a, **k: pytest.fail("Offline"))
    assert runner.run_audit(root) == first
    assert first["summaries"][1]["diagnostic_status"] == "acquisition_failed"
    assert all(not s["original_raw_preserved"] for s in first["summaries"])
    from scripts.report_exp003 import render_audit
    table = render_audit(root)
    assert '| ABT | 2 | 0 |' in table and '| BMY | unavailable |' in table
    (root/'violations.csv').write_bytes(b'changed')
    with pytest.raises(ValueError, match='table hash mismatch'):
        render_audit(root)
