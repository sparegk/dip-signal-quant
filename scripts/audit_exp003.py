"""Quarantine and measure all registered OHLC exclusions; never evaluate returns."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from src.data import download_raw_data
from src.data_audit import audit_ohlc, preserve_raw, restore_raw
from src.preservation import canonical_json, digest, read_record, safe_key, write_record

ROOT = Path(__file__).resolve().parents[1]


def run_audit(root: Path, *, download: bool = False) -> dict:
    """Reuse quarantined bytes offline; never overwrite a completed acquisition."""
    config = json.loads((ROOT / "config/exp003.json").read_text())
    original_path = ROOT / "data/market/exp002-acquisition.json"
    original = json.loads(original_path.read_text())
    failures = {row["ticker"]: row for row in original["exclusions"]}
    summaries, details = [], []
    for ticker in config["audit_tickers"]:
        path = root / "acquisitions" / (safe_key(ticker) + ".json")
        if not path.exists():
            if not download:
                raise FileNotFoundError(f"No preserved diagnostic vintage for {ticker}")
            record = {"ticker": ticker, "vintage": "new_diagnostic", "original_raw_preserved": False,
                      "original_exclusion": failures[ticker],
                      "attempt_started_at": datetime.now(timezone.utc).isoformat()}
            try:
                raw = download_raw_data(ticker, start=config["audit_start"], end=config["audit_end_exclusive"])
                record["snapshot"] = preserve_raw(root, raw)
            except (RuntimeError, ValueError) as error:
                record["acquisition_error"] = str(error)
            write_record(path, record)
        record = read_record(path)
        if "snapshot" not in record:
            summaries.append({"ticker": ticker, "vintage": record["vintage"],
                              "diagnostic_status": "acquisition_failed", **record})
            continue
        raw = restore_raw(root, record["snapshot"])
        summary, findings = audit_ohlc(raw, ticker, vintage=record["vintage"])
        summaries.append(summary | {"snapshot": record["snapshot"], "original_raw_preserved": False})
        details.append(findings)
        print(ticker, summary.get("affected_rows"), summary.get("max_absolute_gap"), flush=True)
    root.mkdir(parents=True, exist_ok=True)
    combined = pd.concat(details, ignore_index=True) if details else pd.DataFrame()
    csv = combined.to_csv(index=False, float_format="%.17g", lineterminator="\n").encode()
    from src.preservation import publish
    publish(root / "violations.csv", csv)
    result = {"experiment": "EXP-003-A", "config_sha256": digest(canonical_json(config)),
              "original_acquisition_sha256": digest(original_path.read_bytes()),
              "violations_sha256": digest(csv), "summaries": summaries}
    write_record(root / "summary.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "data/exp003/diagnostic")
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    run_audit(**vars(args))
