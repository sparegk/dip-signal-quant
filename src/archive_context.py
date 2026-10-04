"""Immutable decision-context sidecars; original EXP-003 records never change."""

import json
from pathlib import Path
from collections.abc import Callable

import pandas as pd

from src.data import load_parquet
from src.features import build_features
from src.paper_archive import ROOT, code_identity, verify_run
from src.preservation import canonical_json, digest, get_object, read_record, safe_key, write_record
from src.research_diagnosis import rebound_paths, support_context
from src.sessions import utc, utc_now
from src.signals import build_signals

CONTEXT_FIELDS = ("open", "high", "low", "close", "volume", "atr_14", "atr_pct_14",
                  "return_5d", "return_10d", "drawdown_60d", "relative_volume_20d",
                  "relative_return_10d", "benchmark_return_20d", "benchmark_drawdown_20d",
                  "benchmark_volatility_20d")


def signal_context(stock: pd.DataFrame, spy: pd.DataFrame, session: str, signal_parameters: dict,
                   context_config: dict) -> dict:
    """Future input rows are excluded before features or prior-outcome memory."""
    day = pd.Timestamp(session)
    stock = stock.loc[stock.timestamp.le(day)].copy()
    spy = spy.loc[spy.timestamp.le(day)].copy()
    if stock.empty or spy.empty or stock.timestamp.max()!=day or spy.timestamp.max()!=day:
        raise ValueError("Signal-date stock and benchmark bars required")
    signals = build_signals(build_features(stock, benchmark=spy), **signal_parameters)
    signals["fold"] = "history"
    rules = {"path_bars":context_config["support"]["maturity_bars"], "rebound_levels":[.02,.05,.10],
             "support":context_config["support"]}
    paths = rebound_paths(signals, rules)
    if paths.empty:
        visits, age = 0, None
    else:
        # Add a context query at the current session even if it is a non-event.
        query = signals.copy()
        query.loc[query.timestamp.eq(day),"dip_event_v1"] = True
        current = support_context(query, paths, rules).iloc[-1]
        visits = int(current.prior_successful_visits)
        age = None if pd.isna(current.days_since_visit) else int(current.days_since_visit)
    row = signals.iloc[-1]
    values = {key:None if pd.isna(row[key]) else float(row[key]) for key in CONTEXT_FIELDS}
    trailing = spy.sort_values("timestamp").close.tail(200)
    mean = float(trailing.mean()) if len(trailing)==200 else None
    return {"features":values, "benchmark_sma200":mean,
            "regime": "unknown" if mean is None else "above" if float(spy.iloc[-1].close)>=mean else "below",
            "prior_successful_visits":visits, "days_since_prior_visit":age,
            "candidate_exit_policies":context_config["candidate_exit_policies"]}


def validate_context(payload: dict) -> None:
    """Allowlist rejects accidental future outcomes in context decision records."""
    if set(payload)!={"schema_version","run_id","session","calculated_at","expected_entry_timestamp",
                      "parent_result_sha256","context_config_sha256","code","snapshot_hashes","records"}:
        raise ValueError("Invalid context envelope fields")
    for row in payload["records"]:
        if set(row)!={"ticker","classification","status","context","error"}:
            raise ValueError("Invalid context record fields")
        c=row["context"]
        if c is not None and (set(c)!={"features","benchmark_sma200","regime","prior_successful_visits",
                                       "days_since_prior_visit","candidate_exit_policies"}
                              or set(c["features"])!=set(CONTEXT_FIELDS) or c["candidate_exit_policies"]!=[]):
            raise ValueError("Unregistered or future context fields")
    canonical_json(payload)


def preserve_context(root: Path, run_id: str, *, clock: Callable[[],str]=utc_now) -> dict:
    """Write once; retry verifies and returns original context, never refreshes data."""
    run_id=safe_key(run_id)
    receipt=verify_run(root,run_id)
    if receipt["status"]=="interrupted":
        raise ValueError("Cannot enrich an interrupted run")
    directory=root/"runs"/run_id
    intent=read_record(directory/"intent.json")
    result=read_record(directory/"result.json")
    target=root/"contexts"/(run_id+".json")
    if target.exists():
        original=read_record(target)
        if original["parent_result_sha256"]!=digest(canonical_json(result)):
            raise ValueError("Context parent changed")
        if digest(get_object(root,original["context_config_sha256"]))!=original["context_config_sha256"]:
            raise ValueError("Context configuration changed")
        validate_context(original)
        seal=root/"context_receipts"/(run_id+".json")
        if seal.exists():
            checked=read_record(seal)
            if checked["context_sha256"]!=digest(canonical_json(original)):
                raise ValueError("Context seal changed")
        else:
            # Interrupted publication cannot retrospectively establish a deadline.
            write_record(seal,{"context_sha256":digest(canonical_json(original)),
                         "published_at":clock(),"classifications":{r["ticker"]:"unverifiable_context"
                         for r in original["records"]},"recovered":True})
        return original
    config_bytes=(ROOT/"config/archive_context.json").read_bytes().replace(b"\r\n",b"\n")
    config=json.loads(config_bytes)
    from src.preservation import put_object
    config_hash=put_object(root,config_bytes)
    protocol=json.loads(get_object(root,intent["config_object"]))
    frames={}
    for ticker,item in result["inputs"].items():
        if item["status"]=="available":
            get_object(root,item["validated_sha256"])
            frames[ticker]=load_parquet(root/"objects"/item["validated_sha256"],ticker=ticker)
    code=code_identity()
    records=[]
    for row in result["records"]:
        record={"ticker":row["ticker"],"classification":"unsealed_context", "status":row["status"],
                "context":None,"error":row["error"]}
        if row["status"]=="available":
            record["context"]=signal_context(frames[row["ticker"]],frames[protocol["benchmark"]],
                                             intent["session"],protocol["signal_parameters"],config)
        records.append(record)
    # Timestamp is acquired after calculations, before the immutable write.
    calculated=clock(); utc(calculated)
    if utc(calculated)<utc(receipt["published_at"]):
        raise ValueError("Context timestamp predates original signal publication")
    payload={"schema_version":1,"run_id":run_id,"session":intent["session"],"calculated_at":calculated,
             "expected_entry_timestamp":intent["calendar"]["next_open"],
             "parent_result_sha256":digest(canonical_json(result)), "context_config_sha256":config_hash,
             "code":code,"snapshot_hashes":{t:item.get("validated_sha256") for t,item in result["inputs"].items()},
             "records":records}
    validate_context(payload)
    write_record(target,payload)
    # Separate seal acquired after context publication; no fabricated backdating.
    published=clock(); utc(published)
    classifications={r["ticker"]: "prospective_context" if receipt["classifications"].get(r["ticker"])=="prospective"
                     and not code["dirty"] and utc(published)<utc(intent["calendar"]["next_open"])
                     and utc(published)>=utc(calculated) else "retrospective_context" for r in records}
    write_record(root/"context_receipts"/(run_id+".json"),{"context_sha256":digest(canonical_json(payload)),
                 "published_at":published,"classifications":classifications})
    return payload


def read_context(root: Path, run_id: str) -> dict | None:
    """Verify an optional sidecar and its seal without changing archive bytes."""
    run_id=safe_key(run_id)
    target=root/"contexts"/(run_id+".json")
    if not target.exists(): return None
    parent=verify_run(root,run_id)
    result=read_record(root/"runs"/run_id/"result.json")
    intent=read_record(root/"runs"/run_id/"intent.json")
    payload=read_record(target); validate_context(payload)
    if payload["parent_result_sha256"]!=digest(canonical_json(result)) or payload["run_id"]!=run_id:
        raise ValueError("Context parent changed")
    get_object(root,payload["context_config_sha256"])
    if payload["snapshot_hashes"]!={t:item.get("validated_sha256") for t,item in result["inputs"].items()}:
        raise ValueError("Context input identity changed")
    seal=root/"context_receipts"/(run_id+".json")
    if not seal.exists():
        return {"payload":payload,"classifications":{r["ticker"]:"unverifiable_context" for r in payload["records"]}}
    receipt=read_record(seal)
    if receipt["context_sha256"]!=digest(canonical_json(payload)):
        raise ValueError("Context seal changed")
    recovered=receipt.get("recovered",False)
    for row in payload["records"]:
        expected="unverifiable_context" if recovered else "prospective_context" if (
            parent["classifications"].get(row["ticker"])=="prospective" and not payload["code"]["dirty"]
            and utc(parent["published_at"])<=utc(payload["calculated_at"])<=utc(receipt["published_at"])
            <utc(intent["calendar"]["next_open"])) else "retrospective_context"
        if receipt["classifications"].get(row["ticker"])!=expected:
            raise ValueError("Context timing classification changed")
    return {"payload":payload,"classifications":receipt["classifications"]}
