"""Manual, append-only signal preservation. No trading or outcome evaluation."""

from collections.abc import Callable
import json
from pathlib import Path
import subprocess
import tempfile

import numpy as np
import pandas as pd

from src.data import PROVENANCE_KEY, clean_data, download_raw_data, load_parquet, save_parquet
from src.data_audit import preserve_raw
from src.features import build_features
from src.preservation import (canonical_json, digest, get_object, put_object, read_record,
                              safe_key, write_record)
from src.sessions import due_sessions, session_facts, timing_classification, utc, utc_now
from src.signals import (COMPONENT_COLUMNS, FEATURE_COLUMNS, THRESHOLD_COLUMNS, build_signals)
from src.universe import membership_mask, static_universe

ROOT = Path(__file__).resolve().parents[1]
CONFIG_SHA256 = "5ddcd87849d98c0966ed62615ad9f4f904bfb32a0d457fed9c69e7864d556dc4"
DECISION_COLUMNS = (*FEATURE_COLUMNS, *THRESHOLD_COLUMNS, *COMPONENT_COLUMNS,
                    "dip_ready_v1", "dip_condition_v1", "dip_event_v1", "dip_component_count")


def load_protocol() -> dict:
    """Refuse configuration drift, including universe changes, before any collection."""
    data = (ROOT / "config/exp003.json").read_bytes().replace(b"\r\n", b"\n")
    if digest(data) != CONFIG_SHA256:
        raise ValueError("Frozen EXP-003 configuration changed")
    config = json.loads(data)
    for name, expected in config["frozen_source_sha256"].items():
        if digest((ROOT / name).read_bytes().replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Frozen V1 source changed")
    if digest((ROOT / "config/exp002.json").read_bytes().replace(b"\r\n", b"\n")) != config["exp002_config_sha256"]:
        raise ValueError("Frozen EXP-002 configuration changed")
    return config


def code_identity() -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    return {"revision": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain")),
            "source_sha256": {path.relative_to(ROOT).as_posix(): digest(path.read_bytes().replace(b"\r\n", b"\n"))
                              for path in sorted((ROOT / "src").glob("*.py"))}}


def _run_dir(root: Path, run_id: str) -> Path:
    return Path(root) / "runs" / safe_key(run_id)


def begin_run(root: Path, run_id: str, *, session: str, mode: str, config: dict, code: dict,
              corrects: str | None = None, reason: str | None = None,
              clock: Callable[[], str] = utc_now) -> dict:
    """Publish intent before acquisition. Same arguments/key return the existing intent."""
    if canonical_json(config) != canonical_json(load_protocol()):
        raise ValueError("Run configuration differs from frozen registration")
    if mode not in {"collect", "replay"}:
        raise ValueError("Unknown collection mode")
    if bool(corrects) != bool(reason):
        raise ValueError("A correction needs a parent and a reason")
    directory = _run_dir(root, run_id)
    facts = session_facts(session)
    identity = {"schema_version": 1, "run_id": run_id, "session": session, "mode": mode,
                "config_sha256": digest(canonical_json(config)), "universe": list(static_universe(config["universe"])),
                "corrects": corrects, "reason": reason}
    if (directory / "intent.json").exists():
        existing = read_record(directory / "intent.json")
        if any(existing.get(key) != value for key, value in identity.items()):
            raise ValueError("Conflicting run identity; use an explicit correction")
        return existing
    previous = []
    for path in (Path(root) / "runs").glob("*/intent.json"):
        record = read_record(path)
        if record["session"] == session:
            previous.append(record)
    if previous:
        if corrects not in {row["run_id"] for row in previous}:
            raise ValueError("Another run exists for this session; reference it explicitly")
        if any(row["corrects"] == corrects for row in previous):
            raise ValueError("Correction already has a successor; use its latest version")
        parent = read_record(_run_dir(root, corrects) / "intent.json")
        if parent["config_sha256"] != identity["config_sha256"]:
            raise ValueError("Correction must retain registered configuration")
    elif corrects:
        raise ValueError("Correction parent does not exist for this session")
    # Atomic identity reservations also prevent concurrent writers from creating
    # two primary runs or two competing corrections for one predecessor.
    claim = (Path(root) / "successors" / (safe_key(corrects) + ".json") if corrects
             else Path(root) / "sessions" / (session + ".json"))
    write_record(claim, identity)
    started = clock()
    utc(started)
    payload = identity | {"started_at": started, "calendar": facts, "code": code,
                          "config_object": put_object(root, canonical_json(config))}
    write_record(directory / "intent.json", payload)
    return payload


def capture_input(root: Path, ticker: str, *, config: dict, session: str,
                  replay_cache: Path | None = None) -> dict:
    """Use existing data APIs, keeping raw failures and validated byte vintages."""
    result = {"ticker": ticker, "status": "unavailable", "error": None}
    try:
        if replay_cache is not None:
            path = replay_cache / (ticker + ".parquet")
            data = path.read_bytes()
            result["validated_sha256"] = put_object(root, data)
            frame = load_parquet(Path(root) / "objects" / result["validated_sha256"], ticker=ticker)
            result["input_kind"] = "historical_cache_replay"
        else:
            end = (pd.Timestamp(session) + pd.Timedelta(days=1)).date().isoformat()
            raw = download_raw_data(ticker, start=config["history_start"], end=end)
            result.update(preserve_raw(root, raw))
            result["input_kind"] = "new_provider_vintage"
            frame = clean_data(raw, ticker)
            if ((frame.timestamp < pd.Timestamp(config["history_start"])).any()
                    or (frame.timestamp >= pd.Timestamp(end)).any()):
                raise ValueError("Provider response outside requested dates")
            with tempfile.TemporaryDirectory(dir=root) as temporary:
                path = Path(temporary) / "validated.parquet"
                save_parquet(frame, path)
                result["validated_sha256"] = put_object(root, path.read_bytes())
        result.update(status="available", provenance=frame.attrs[PROVENANCE_KEY],
                      latest_session=frame.timestamp.max().date().isoformat(), rows=len(frame))
    except (RuntimeError, ValueError, OSError, TypeError) as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def _scalar(value):
    if pd.isna(value):
        return None
    return value.item() if isinstance(value, np.generic) else value


def decision_records(root: Path, intent: dict, inputs: dict) -> list[dict]:
    """Deterministically replay the frozen V1 prefix; retain each requested ticker."""
    config = json.loads(get_object(root, intent["config_object"]))
    day = pd.Timestamp(intent["session"])
    frames = {}
    for ticker, item in inputs.items():
        if item["status"] == "available":
            get_object(root, item["validated_sha256"])
            frame = load_parquet(Path(root) / "objects" / item["validated_sha256"], ticker=ticker)
            if (frame.timestamp.max().date().isoformat() != item["latest_session"]
                    or len(frame) != item["rows"] or frame.attrs[PROVENANCE_KEY] != item["provenance"]):
                raise ValueError("Input descriptor differs from preserved snapshot")
            frames[ticker] = frame.loc[frame.timestamp <= day].copy()
    spy = frames.get(config["benchmark"])
    records = []
    for ticker in intent["universe"]:
        identity = pd.DataFrame({"timestamp": [day], "ticker": [ticker]})
        record = {"record_id": intent["run_id"] + ":" + ticker, "ticker": ticker,
                  "session": intent["session"], "eligible": bool(membership_mask(identity, config["universe"]).iloc[0]),
                  "status": "unavailable", "error": None, "values": None}
        stock = frames.get(ticker)
        if stock is None:
            record["error"] = inputs[ticker].get("error", "Stock unavailable")
        elif spy is None or spy.empty:
            record["error"] = "Benchmark unavailable: " + str(inputs[config["benchmark"]].get("error"))
        elif stock.empty or stock.timestamp.max() != day or spy.timestamp.max() != day:
            record.update(status="stale", error="Signal-date stock or SPY bar unavailable")
        else:
            try:
                signals = build_signals(build_features(stock, benchmark=spy), **config["signal_parameters"])
                row = signals.iloc[-1]
                record.update(status="available", values={name: _scalar(row[name]) for name in DECISION_COLUMNS})
            except (ValueError, TypeError) as error:
                record["error"] = f"Decision failed: {error}"
        records.append(record)
    return records


def validate_records(intent: dict, records: list[dict]) -> None:
    """Reject omissions, duplicates, invalid flags and inconsistent decision values."""
    if [row["ticker"] for row in records] != intent["universe"]:
        raise ValueError("Records must contain the exact ordered universe")
    for row in records:
        if (row["session"] != intent["session"] or row["record_id"] != intent["run_id"] + ":" + row["ticker"]
                or type(row["eligible"]) is not bool or row["status"] not in {"available", "unavailable", "stale"}):
            raise ValueError("Invalid signal record schema")
        values = row["values"]
        if row["status"] != "available":
            if values is not None or not row["error"]:
                raise ValueError("Failed decisions need null values and an explicit error")
            continue
        if values is None or set(values) != set(DECISION_COLUMNS):
            raise ValueError("Incomplete decision schema")
        for name in (*FEATURE_COLUMNS, *THRESHOLD_COLUMNS):
            if values[name] is not None and (type(values[name]) not in {int, float} or not np.isfinite(values[name])):
                raise ValueError("Feature/threshold must be finite numeric or null")
        for feature, threshold, component in zip(FEATURE_COLUMNS, THRESHOLD_COLUMNS, COMPONENT_COLUMNS):
            expected = (values[feature] is not None and values[threshold] is not None
                        and values[feature] <= values[threshold])
            if values[component] != expected:
                raise ValueError("Component differs from frozen comparison")
        flags = (*COMPONENT_COLUMNS, "dip_ready_v1", "dip_condition_v1", "dip_event_v1")
        if any(type(values[key]) is not bool for key in flags):
            raise ValueError("Decision flags must be boolean")
        count = values["dip_component_count"]
        if type(count) is not int or count != sum(values[key] for key in COMPONENT_COLUMNS):
            raise ValueError("Invalid component count")
        ready = all(values[key] is not None for key in (*FEATURE_COLUMNS, *THRESHOLD_COLUMNS))
        if (ready != values["dip_ready_v1"]
                or values["dip_condition_v1"] != (ready and count >= 3)
                or (values["dip_event_v1"] and not values["dip_condition_v1"])):
            raise ValueError("Inconsistent frozen signal flags")
    canonical_json(records)  # rejects nonfinite values anywhere


def classifications(intent: dict, result: dict, published_at: str, config: dict) -> dict:
    output = {}
    for row in result["records"]:
        sources = [result["inputs"][ticker] for ticker in (row["ticker"], config["benchmark"])]
        unverifiable = any(source.get("input_kind") != "new_provider_vintage" for source in sources)
        try:
            unverifiable |= any(utc(source.get("provenance", {}).get("retrieved_at", ""))
                                > utc(result["calculated_at"]) for source in sources)
        except (TypeError, ValueError):
            unverifiable = True
        output[row["ticker"]] = timing_classification(
            facts=intent["calendar"], published_at=published_at, mode=intent["mode"],
            effective_session=config["effective_session"], clean_revision=not intent["code"]["dirty"],
            available=row["status"] != "unavailable", correction=bool(intent["corrects"]),
            latest_sessions=[source.get("latest_session", "") for source in sources],
            source_times=[source.get("provenance", {}).get("retrieved_at", "") for source in sources],
            has_future_input=unverifiable or any(source.get("latest_session", "") > intent["session"] for source in sources))
    return output


def finish_run(root: Path, intent: dict, inputs: dict, *, clock: Callable[[], str] = utc_now) -> dict:
    """Publish original result first; seal with an actual AFTER-publication timestamp."""
    directory = _run_dir(root, intent["run_id"])
    if (directory / "recovery.json").exists():
        raise ValueError("Recovered incomplete runs cannot be finalized")
    if (directory / "result.json").exists():
        raise ValueError("Result already exists; verify it, never silently reseal an interruption")
    config = json.loads(get_object(root, intent["config_object"]))
    if set(inputs) != set(intent["universe"]) | {config["benchmark"]}:
        raise ValueError("Missing requested inputs")
    records = decision_records(root, intent, inputs)
    validate_records(intent, records)
    count = sum(row["status"] == "available" for row in records)
    status = "complete" if count == len(records) else ("partial" if count else "failed")
    calculated_at = clock()
    if utc(calculated_at) < utc(intent["started_at"]):
        raise ValueError("Clock moved backwards")
    result = {"schema_version": 1, "run_id": intent["run_id"], "inputs": inputs,
              "records": records, "calculated_at": calculated_at, "status": status,
              "intent_sha256": digest(canonical_json(intent))}
    write_record(directory / "result.json", result)
    published_at = clock()
    if utc(published_at) < utc(calculated_at):
        raise ValueError("Clock moved backwards; result remains unsealed")
    receipt = {"run_id": intent["run_id"], "published_at": published_at,
               "result_sha256": digest(canonical_json(result)),
               "classifications": classifications(intent, result, published_at, config)}
    write_record(directory / "receipt.json", receipt)
    return receipt


def verify_run(root: Path, run_id: str, *, replay: bool = False) -> dict:
    """Check linked records and EVERY retained input; optional offline decision replay."""
    directory = _run_dir(root, run_id)
    intent = read_record(directory / "intent.json")
    if intent["run_id"] != run_id or intent["session"] != intent["calendar"]["session"]:
        raise ValueError("Run identity mismatch")
    config = json.loads(get_object(root, intent["config_object"]))
    if digest(canonical_json(config)) != intent["config_sha256"]:
        raise ValueError("Config hash mismatch")
    # Even unsealed/interrupted attempts retain and verify acquired input vintages.
    acquired = {}
    for path in (directory / "inputs").glob("*.json"):
        item = read_record(path)
        if path.stem != item["ticker"]:
            raise ValueError("Acquisition identity mismatch")
        acquired[item["ticker"]] = item
        for key in ("raw_sha256", "validated_sha256"):
            if key in item:
                get_object(root, item[key])
    if (directory / "result.json").exists():
        pending = read_record(directory / "result.json")
        if pending["intent_sha256"] != digest(canonical_json(intent)):
            raise ValueError("Run linkage hash mismatch")
        for ticker, item in acquired.items():
            if pending["inputs"].get(ticker) != item:
                raise ValueError("Acquisition differs from result")
        for item in pending["inputs"].values():
            for key in ("raw_sha256", "validated_sha256"):
                if key in item:
                    get_object(root, item[key])
    if (directory / "recovery.json").exists():
        recovery = read_record(directory / "recovery.json")
        if recovery["intent_sha256"] != digest(canonical_json(intent)):
            raise ValueError("Recovery identity mismatch")
        return {"run_id": run_id, "status": "interrupted", "classifications": {}}
    if not (directory / "result.json").exists() or not (directory / "receipt.json").exists():
        return {"run_id": run_id, "status": "interrupted", "classifications": {}}
    result, receipt = read_record(directory / "result.json"), read_record(directory / "receipt.json")
    if (result["intent_sha256"] != digest(canonical_json(intent))
            or receipt["result_sha256"] != digest(canonical_json(result))):
        raise ValueError("Run linkage hash mismatch")
    if not utc(intent["started_at"]) <= utc(result["calculated_at"]) <= utc(receipt["published_at"]):
        raise ValueError("Invalid publication chronology")
    validate_records(intent, result["records"])
    if set(result["inputs"]) != set(intent["universe"]) | {config["benchmark"]}:
        raise ValueError("Missing archived input identities")
    count = sum(row["status"] == "available" for row in result["records"])
    expected_status = "complete" if count == len(intent["universe"]) else ("partial" if count else "failed")
    if result["status"] != expected_status:
        raise ValueError("Invalid run completion status")
    for item in result["inputs"].values():
        for key in ("raw_sha256", "validated_sha256"):
            if key in item:
                get_object(root, item[key])
    expected = classifications(intent, result, receipt["published_at"], config)
    if receipt["classifications"] != expected:
        raise ValueError("Invalid timing classifications")
    if replay and decision_records(root, intent, result["inputs"]) != result["records"]:
        raise ValueError("Decision replay mismatch")
    return receipt | {"status": result["status"]}


def recover_run(root: Path, run_id: str, *, clock: Callable[[], str] = utc_now) -> dict:
    """Mark an interrupted attempt explicitly; never publish it retroactively."""
    directory = _run_dir(root, run_id)
    if (directory / "receipt.json").exists():
        raise ValueError("A sealed run cannot be recovered or overwritten")
    path = directory / "recovery.json"
    if path.exists():
        return read_record(path)
    intent = read_record(directory / "intent.json")
    recovered_at = clock()
    if utc(recovered_at) < utc(intent["started_at"]):
        raise ValueError("Recovery clock moved backwards")
    recovery = {"run_id": run_id, "status": "interrupted", "recovered_at": recovered_at,
                "intent_sha256": digest(canonical_json(intent)),
                "reason": "Unsealed attempt retained; collect under a new correction key"}
    write_record(path, recovery)
    return recovery


def coverage(root: Path, config: dict, *, as_of: str) -> list[dict]:
    """Operational coverage only: no returns, no automatic performance inspection."""
    by_session = {}
    for path in (Path(root) / "runs").glob("*/intent.json"):
        intent = read_record(path)
        if intent["corrects"] is None:
            by_session[intent["session"]] = verify_run(root, intent["run_id"])
    return [{"session": day, **by_session.get(day, {"status": "missing_run", "classifications": {}})}
            for day in due_sessions(config["effective_session"], as_of)]
