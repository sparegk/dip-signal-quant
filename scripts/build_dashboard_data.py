"""Read-only, offline research export: python -m scripts.build_dashboard_data.

Historical statistics come from existing reports, never from browser calculations.
EXP-001 detail ledgers are reconstructed with the existing frozen Python APIs and
verified source snapshots; its saved statistics are not refitted or recomputed.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.backtest import assign_research_splits, compute_forward_outcomes, simulate_barrier_trades
from src.data import load_parquet
from src.features import build_features
from src.paper_archive import coverage, verify_run
from src.preservation import canonical_json, digest, publish, read_record
from src.signals import build_signals

ROOT = Path(__file__).resolve().parents[1]


def safe_json(value):
    if isinstance(value, dict):
        return {str(k): safe_json(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [safe_json(v) for v in value]
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not np.isfinite(value):
        return None
    return value


def records(frame: pd.DataFrame) -> list[dict]:
    return safe_json(frame.to_dict("records"))


def checked_bytes(path: Path, expected: str) -> bytes:
    data = path.read_bytes()
    if digest(data) != expected:
        raise ValueError(f"Research input hash mismatch: {path.name}")
    return data


def comparisons(frame: pd.DataFrame, group: str | None = None) -> list[dict]:
    """Presentation differences; paired SPY excess comes directly from Python results."""
    output = []
    groups = [(None, frame)] if group is None else frame.groupby(group, sort=True)
    for label, part in groups:
        for horizon, rows in part.groupby("horizon", sort=True):
            selections = rows.set_index("selection")
            event = selections.loc["events"].to_dict()
            unconditional, non_signal = selections.loc["eligible", "mean"], selections.loc["non_signal", "mean"]
            output.append({**event, "horizon": int(horizon), "group": str(label) if label is not None else "pooled",
                           "unconditional": unconditional, "non_signal": non_signal,
                           "difference_unconditional": event["mean"] - unconditional,
                           "difference_non_signal": event["mean"] - non_signal,
                           "difference_spy": event["mean_excess_return"]})
    return safe_json(output)


def feature_catalog() -> list[dict]:
    """Definitions describe the existing defaults; no feature computations live here."""
    result = []
    def add(key, group, window, formula, interpretation, warmup, unit="percent", data="Adjusted close"):
        result.append(dict(key=key, group=group, window=str(window), formula=formula,
                           interpretation=interpretation, warmup=warmup, unit=unit, data=data,
                           availability="After the current session closes; observed-bar windows",
                           used_in_v1=key in {"drawdown_60d", "distance_from_low_20d", "price_zscore_20d", "relative_return_10d"}))
    for n in (1, 5, 10, 20):
        add(f"return_{n}d", "Returns", n, f"C(t) / C(t-{n}) - 1", "Trailing price change, not a future outcome.", f"First {n} observations undefined")
    for n in (20, 60):
        for prefix, group, formula, interpretation in (
            ("drawdown", "Drawdown", "C(t) / max(C) - 1", "Distance below the trailing highest close."),
            ("distance_from_high", "Price location", "C(t) / max(C) - 1", "Same quantity as drawdown; not an independent feature."),
            ("distance_from_low", "Price location", "C(t) / min(C) - 1", "Distance above the trailing lowest close.")):
            add(f"{prefix}_{n}d", group, n, formula, interpretation, f"First {n-1} observations undefined")
    add("price_zscore_20d", "Z-score", 20, "(C(t) - mean20(C)) / sample_std20(C)", "Standardized price location; not a probability.", "19 observations; zero standard deviation is undefined", "number")
    add("rsi_14", "Momentum", 14, "100 × Wilder(gains) / (Wilder(gains) + Wilder(losses))", "Balance of smoothed up/down changes; no trading cutoff.", "First 14 observations; flat history undefined", "number")
    add("true_range", "ATR", "Previous close", "max(H-L, |H-Cprev|, |L-Cprev|)", "Daily range including overnight gaps.", "First observation undefined", "price", "Adjusted high, low and close")
    add("atr_14", "ATR", 14, "ATR(t) = (13 × ATR(t-1) + TR(t)) / 14", "Wilder-smoothed absolute movement scale.", "Arithmetic seed from first 14 defined ranges", "price", "Adjusted high, low and close")
    add("atr_pct_14", "ATR", 14, "ATR14 / C(t)", "Range scaled by current adjusted price.", "First 14 observations undefined")
    for n in (20, 60):
        add(f"volatility_{n}d", "Volatility", n, f"sample_std{n}(daily return) × sqrt(252)", "Annualized historical variation, not forecast risk.", f"First {n} observations undefined")
    for key, formula, interpretation, unit in (
        ("volume_mean_20d", "mean20(V)", "Trailing reported activity.", "number"),
        ("relative_volume_20d", "V(t) / mean20(V)", "Activity relative to recent history.", "number"),
        ("volume_zscore_20d", "(V(t) - mean20(V)) / sample_std20(V)", "Standardized activity.", "number")):
        add(key, "Volume", 20, formula, interpretation, "19 observations; zero denominator undefined", unit, "Provider-reported volume")
    for n in (5, 10, 20):
        add(f"relative_return_{n}d", "Benchmark-relative", n, f"[C(t)/C(t-{n})-1] - [SPY(t)/SPY(t-{n})-1]", "Trailing stock minus SPY over identical endpoints.", f"{n} observations; missing SPY endpoints undefined", data="Stock and SPY adjusted close")
    for key, formula, interpretation, warmup in (
        ("benchmark_return_20d", "SPY(t) / SPY(t-20) - 1", "SPY's own trailing return.", "20 SPY observations"),
        ("benchmark_drawdown_20d", "SPY(t) / max20(SPY) - 1", "SPY's trailing price location.", "19 SPY observations"),
        ("benchmark_volatility_20d", "sample_std20(SPY daily return) × sqrt(252)", "SPY's historical variation.", "20 SPY observations")):
        add(key, "Benchmark-relative", 20, formula, interpretation, warmup + "; exact-date match required", data="SPY adjusted close")
    return result


def history_payload(observations: pd.DataFrame, events: pd.DataFrame, trades: pd.DataFrame,
                    ticker: str, experiment: str) -> dict:
    """Keep signal-time rows and future-outcome ledgers in separate schema fields."""
    rows = observations.loc[observations.ticker.eq(ticker)].sort_values("timestamp").copy()
    rows["date"] = rows.timestamp.dt.strftime("%Y-%m-%d")
    if "split" not in rows:
        rows["split"] = "test"
    if "fold" not in rows:
        rows["fold"] = rows["split"]
    rows["fold"] = rows.fold.astype(str)
    rows = rows.drop(columns=["timestamp", "ticker"])
    known = {"columns": list(rows.columns), "rows": safe_json(rows.to_numpy().tolist())}
    future = {}
    for source, kind in ((events, "horizons"), (trades, "trades")):
        selected = source.loc[source.ticker.eq(ticker)]
        for stamp, group in selected.groupby("timestamp", sort=True):
            future.setdefault(stamp.strftime("%Y-%m-%d"), {})[kind] = records(group.drop(columns=["ticker", "timestamp"]))
    return {"schema_version": 1, "ticker": ticker, "experiment": experiment,
            "known_at_signal": known, "future_outcomes": future,
            "availability": "Historical adjusted vintage; computationally causal, not point-in-time"}


def export_exp002(root: Path) -> tuple[dict, dict[str, dict]]:
    directory = root / "results/exp_002"
    path = directory / "metadata.json"
    if not path.exists():
        return {"status": "missing", "reason": "Preserved EXP-002 result artifacts are not available locally."}, {}
    metadata = json.loads(path.read_bytes())
    for name, expected in metadata["artifact_sha256"].items():
        if Path(name).name != name:
            raise ValueError("Unsafe artifact path")
        checked_bytes(directory / name, expected)
    tables = {Path(name).stem: pd.read_csv(directory / name, float_precision="round_trip")
              for name in metadata["artifact_sha256"] if name.endswith(".csv")}
    observations = pd.read_parquet(directory / "observations.parquet")
    events = pd.read_parquet(directory / "events.parquet")
    trades = pd.read_parquet(directory / "trades.parquet")
    comparison = comparisons(tables["oos_summary"])
    fold_comparison = comparisons(tables["fold_summary"], "fold")
    frequency = tables["frequency_fold"]
    folds = []
    for fold in metadata["folds"]:
        label = str(fold["fold"])
        outcome = next(row for row in fold_comparison if row["group"] == label and row["horizon"] == 10)
        trade = tables["trade_fold_summary"].loc[(tables["trade_fold_summary"].fold.astype(str) == label)
                                               & tables["trade_fold_summary"]["mode"].eq("non_overlapping")].iloc[0].to_dict()
        freq = frequency.loc[frequency.fold.astype(str).eq(label)].iloc[0].to_dict()
        folds.append({**fold, "events": int(freq["events"]), "event_mean": outcome["mean"],
                      "spy_excess": outcome["difference_spy"], "net_mean": trade["average_return"],
                      "win_rate": trade["win_rate"], "profit_factor": trade["profit_factor"],
                      "condition_fraction": freq["condition_fraction_ready"], "frequency": freq["events_per_252_ready"]})
    histograms = {}
    for key, table, column in (("gross", tables["ticker_summary"].query("selection == 'events' and horizon == 10"), "mean"),
                               ("excess", tables["ticker_summary"].query("selection == 'events' and horizon == 10"), "mean_excess_return"),
                               ("expectancy", tables["trade_ticker_summary"].query("mode == 'non_overlapping'"), "average_return")):
        values = table[column].dropna()
        counts, edges = np.histogram(values, bins=12)
        histograms[key] = [dict(lower=float(edges[i]), upper=float(edges[i+1]), center=float((edges[i]+edges[i+1])/2), count=int(n))
                           for i, n in enumerate(counts)]
    exit_counts = records(trades.loc[trades.status.eq("completed")].groupby(["mode", "exit_reason"]).size().rename("count").reset_index())
    distribution = tables["distribution"]
    excess = distribution.loc[(distribution.horizon == 10) & distribution.metric.eq("mean_excess_return")].iloc[0]
    favorable_folds = sum(row["mean"] > row["unconditional"] and row["difference_spy"] > 0
                          for row in fold_comparison if row["horizon"] == 10)
    ready, event_count, conditions = (int(frequency[c].sum()) for c in ("ready", "events", "conditions"))
    ledger = records(observations.loc[observations.dip_event_v1, ["timestamp", "ticker", "fold", "dip_component_count", "regime"]])
    result = {"status": "available", "metadata": metadata, "source_sha256": digest(path.read_bytes()),
              "tables": {key: records(value) for key, value in tables.items()}, "comparison": comparison,
              "folds": folds, "histograms": histograms, "exit_counts": exit_counts, "event_ledger": ledger,
              "frequency": {"events": event_count, "ready": ready, "conditions": conditions,
                            "condition_fraction": conditions / ready, "events_per_252_ready": 252 * event_count / ready},
              "criteria": {"breadth_passed": bool(excess.positive_count > excess.defined_count / 2),
                           "positive_excess_tickers": int(excess.positive_count), "defined_tickers": int(excess.defined_count),
                           "favorable_folds": favorable_folds, "fold_count": len(folds), "concentration_threshold": .5}}
    series = {f"EXP-002/{ticker}": history_payload(observations, events, trades, ticker, "EXP-002")
              for ticker in metadata["usable_tickers"]}
    return safe_json(result), series


def export_exp001(root: Path, config: dict) -> tuple[dict, dict[str, dict]]:
    path = root / "data/exp001-verification.json"
    if not path.exists():
        return {"status": "missing", "reason": "Saved EXP-001 verification JSON is not available locally."}, {}
    report = json.loads(path.read_bytes())
    for name, expected in config["frozen_source_sha256"].items():
        if digest((root / name).read_bytes().replace(b"\r\n", b"\n")) != expected:
            raise ValueError("Frozen feature/signal source differs; refusing explorer reconstruction")
    frames = {}
    for ticker, snapshot in report["snapshots"].items():
        file = root / "data/market" / (ticker + ".parquet")
        checked_bytes(file, snapshot["sha256"])
        frames[ticker] = load_parquet(file, ticker=ticker)
    symbols = sorted(set(frames) - {"SPY"})
    stocks = pd.concat([frames[s] for s in symbols], ignore_index=True).sort_values(["timestamp", "ticker"]).reset_index(drop=True)
    stocks.attrs = {}
    signals = build_signals(build_features(stocks, benchmark=frames["SPY"]), **config["signal_parameters"])
    split = assign_research_splits(signals, validation_start=report["split_parameters"]["validation_start"],
                                   test_start=report["split_parameters"]["test_start"])
    events = compute_forward_outcomes(split, benchmark=frames["SPY"], horizons=config["horizons"])
    trades = pd.concat([simulate_barrier_trades(split, mode=mode, **config["barrier_parameters"]).assign(mode=mode)
                        for mode in ("independent", "non_overlapping")], ignore_index=True)
    summary = pd.DataFrame([dict(row, selection=selection) for selection, rows in report["forward_summaries"].items() for row in rows])
    return {"status": "available", "report": report, "source_sha256": digest(path.read_bytes()),
            "comparison": comparisons(summary, "split")}, {
        f"EXP-001/{ticker}": history_payload(split, events, trades, ticker, "EXP-001") for ticker in symbols}


def export_archive(root: Path, config: dict, as_of: str) -> dict:
    directory = root / "data/paper_archive"
    runs, rows = [], []
    for path in sorted(directory.glob("runs/*/intent.json")):
        intent = read_record(path)
        verified = verify_run(directory, intent["run_id"])
        run = {"run_id": intent["run_id"], "session": intent["session"], "mode": intent["mode"],
               "started_at": intent["started_at"], "published_at": verified.get("published_at"),
               "status": verified["status"], "code_revision": intent["code"]["revision"],
               "code_dirty": intent["code"]["dirty"], "config_hash": intent["config_sha256"],
               "corrects": intent["corrects"]}
        runs.append(run)
        if verified["status"] == "interrupted":
            continue
        result = read_record(path.parent / "result.json")
        for row in result["records"]:
            source = result["inputs"][row["ticker"]]
            rows.append({**run, **row, "run_status": run["status"], "classification": verified["classifications"][row["ticker"]],
                         "input_hash": source.get("validated_sha256", source.get("raw_sha256")),
                         "retrieved_at": source.get("provenance", {}).get("retrieved_at"),
                         # Do not export raw exception strings containing local filesystem paths.
                         "error": "Input unavailable; inspect the local archive for details" if row["error"] else None,
                         "outcome": None})
    return {"status": "initialized" if directory.exists() else "not_collected", "config": config,
            "runs": runs, "records": rows, "coverage": coverage(directory, config, as_of=as_of),
            "prospective_count": sum(r["classification"] == "prospective" for r in rows),
            "retrospective_count": sum(r["classification"] == "retrospective" for r in rows),
            "non_event_count": sum(r["values"] is not None and not r["values"]["dip_event_v1"] for r in rows),
            "failure_count": sum(r["values"] is None for r in rows), "as_of": as_of}


def export_audit(root: Path) -> dict:
    directory = root / "data/exp003/diagnostic_authorized"
    if not (directory / "summary.json").exists():
        return {"status": "missing", "reason": "Preserved EXP-003 diagnostic artifacts are unavailable."}
    from scripts.report_exp003 import render_audit
    render_audit(directory)  # verifies summary values against retained raw vintages
    report = read_record(directory / "summary.json")
    summaries = [{key: value for key, value in row.items() if key != "snapshot"} |
                 {"retrieved_at": row.get("snapshot", {}).get("provenance", {}).get("retrieved_at")}
                 for row in report["summaries"]]
    return {"status": "available", "summaries": summaries,
            "rows": sum(row.get("rows", 0) for row in summaries),
            "affected_rows": sum(row.get("affected_rows", 0) for row in summaries),
            "violations": records(pd.read_csv(directory / "violations.csv", float_precision="round_trip")),
            "source_sha256": digest((directory / "summary.json").read_bytes())}


def documentation(root: Path) -> dict:
    docs = {p.stem: p.read_text(encoding="utf-8") for p in sorted((root / "docs").glob("*.md"))}
    log = []
    for match in re.finditer(r"^## (\d{4}-\d{2}-\d{2})[^\n]*\n", docs.get("RESEARCH_LOG", ""), re.M):
        end = docs["RESEARCH_LOG"].find("\n## ", match.end())
        log.append({"date": match.group(1), "title": match.group(0).strip()[3:],
                    "body": docs["RESEARCH_LOG"][match.end():end if end >= 0 else None].strip()})
    roadmap_text = (root / "ROADMAP.md").read_text(encoding="utf-8")
    roadmap = [{"title": title, "status": "completed" if checked == "x" else
                ("prospective" if "Prospective outcome" in title else "not_started")}
               for checked, title in re.findall(r"^- \[([ x])\] (.+)$", roadmap_text, re.M)]
    experiments = []
    text = docs.get("EXPERIMENTS", "")
    headings = list(re.finditer(r"^## (EXP-\d{3})[^\n]*", text, re.M))
    for i, match in enumerate(headings):
        experiments.append({"id": match.group(1), "title": match.group(0)[3:], "status": "complete",
                            "body": text[match.end():headings[i+1].start() if i+1 < len(headings) else None].strip(),
                            "doc": "EXPERIMENTS"})
    return {"documents": docs, "research_log": list(reversed(log)), "roadmap": roadmap,
            "experiments": experiments, "last_research_update": max((row["date"] for row in log), default=None)}


def build_dashboard(root: Path = ROOT, output: Path | None = None, *, as_of: str | None = None) -> dict:
    """Publish immutable generation files, then atomically switch the small manifest."""
    output = output or root / "frontend/public/data"
    as_of = as_of or datetime.now(timezone.utc).isoformat()
    config = json.loads((root / "config/exp003.json").read_bytes())
    with patch("yfinance.download", side_effect=AssertionError("Dashboard export is strictly offline")):
        exp002, series2 = export_exp002(root)
        exp001, series1 = export_exp001(root, config)
        archive = export_archive(root, config, as_of)
        audit = export_audit(root)
    docs = documentation(root)
    data = {"schema_version": 1, "as_of": as_of, "exp001": exp001, "exp002": exp002,
            "archive": archive, "audit": audit, "feature_catalog": feature_catalog(), **docs}
    files = {"dashboard.json": canonical_json(safe_json(data))}
    for key, value in (series1 | series2).items():
        files["series/" + key + ".json"] = canonical_json(safe_json(value))
    hashes = {key: digest(value) for key, value in sorted(files.items())}
    generation = digest(canonical_json(hashes))[:24]
    for name, content in files.items():
        publish(output / "generations" / generation / name, content)
    manifest = {"schema_version": 1, "generation": generation, "as_of": as_of,
                "dashboard": f"generations/{generation}/dashboard.json", "sha256": hashes,
                "series": {key: f"generations/{generation}/series/{key}.json" for key in sorted(series1 | series2)}}
    output.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".manifest-", dir=output)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical_json(manifest))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, output / "manifest.json")
    finally:
        Path(name).unlink(missing_ok=True)
    return {"generation": generation, "ticker_files": len(series1 | series2), "bytes": sum(map(len, files.values())),
            "sources": {"EXP-001": exp001["status"], "EXP-002": exp002["status"], "EXP-003": audit["status"]}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--as-of", help="Coverage cutoff for reproducible export, never a collection timestamp")
    args = parser.parse_args()
    print(json.dumps(build_dashboard(output=args.output, as_of=args.as_of), indent=2))
