"""Frozen EXP-002: optional cache acquisition, then deterministic offline evaluation."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.data import DEFAULT_CACHE_DIR, PROVENANCE_KEY, get_history
from src.features import build_features
from src.robustness import summarize_robustness
from src.signals import build_signals
from src.universe import select_universe
from src.walkforward import annual_folds, evaluate_fold


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "exp002.json"
PREREGISTRATION = "ff6a99d"


def json_safe(value):
    """Portable deterministic JSON: undefined statistics become null."""
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_safe(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    return value


def write_json(path: Path, value: dict) -> None:
    """Write stable JSON, including undefined statistics explicitly."""
    path.write_text(json.dumps(json_safe(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
                    encoding="utf-8")


def load_config(path: Path = CONFIG) -> dict:
    """Reject accidental changes to the registered signal/feature implementation."""
    config = json.loads(path.read_text(encoding="utf-8"))
    for filename, expected in config["frozen_source_sha256"].items():
        actual = sha256((ROOT / filename).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        if actual != expected:
            raise ValueError(f"Frozen V1 source changed: {filename}")
    return config


def acquire_data(config: dict, cache_dir: Path, *, download: bool = False) -> tuple[dict, list[dict], dict]:
    """Use existing market-data APIs; never refresh or conceal corrupt cache failures."""
    symbols = select_universe(config["source_tickers"], exclude=config["excluded_tickers"])
    snapshots, exclusions, provenance = {}, [], {}
    acquisition_path = cache_dir / "exp002-acquisition.json"
    config_digest = sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    previous_failures = {}
    if acquisition_path.exists() and not download:
        acquisition = json.loads(acquisition_path.read_text(encoding="utf-8"))
        if acquisition["config_digest"] == config_digest:
            previous_failures = {row["ticker"]: row for row in acquisition["exclusions"]}
    for ticker in (config["benchmark"], *symbols):
        path = cache_dir / f"{ticker}.parquet"
        if not path.exists() and not download:
            if ticker == config["benchmark"]:
                raise FileNotFoundError(f"Missing benchmark cache: {path}")
            exclusions.append(previous_failures.get(ticker, {
                "ticker": ticker, "fold": "all", "reason": "missing_cache", "detail": ""}))
            continue
        attempts = 1 if path.exists() else 2
        for attempt in range(attempts):
            try:
                frame = get_history(ticker, cache_dir=cache_dir, start=config["start"],
                                    end=config["end_exclusive"])
            except (RuntimeError, ValueError) as error:
                if path.exists() or ticker == config["benchmark"]:
                    raise
                if attempt + 1 == attempts:
                    exclusions.append({"ticker": ticker, "fold": "all", "reason": "download_or_validation_failed",
                                       "detail": str(error)})
            else:
                snapshots[ticker] = frame
                provenance[ticker] = {"sha256": sha256(path.read_bytes()).hexdigest(),
                                      "rows": len(frame), "start": frame.timestamp.min(),
                                      "end": frame.timestamp.max(), "source": frame.attrs[PROVENANCE_KEY]}
                break
        print(f"Cache {ticker}: {'available' if ticker in snapshots else 'excluded'}", file=sys.stderr, flush=True)
    if download:
        write_json(acquisition_path, {"config_digest": config_digest, "exclusions": exclusions,
                                      "snapshots": provenance})
    return snapshots, exclusions, provenance


def evaluate_snapshots(snapshots: dict[str, pd.DataFrame], config: dict) -> tuple[dict, dict, list[dict]]:
    """Pure cached-frame evaluation; no network, output writing or parameter search."""
    requested = select_universe(config["source_tickers"], exclude=config["excluded_tickers"])
    spy = snapshots[config["benchmark"]]
    folds = annual_folds(spy.timestamp, initial_history_years=config["initial_history_years"])
    symbols = tuple(ticker for ticker in requested if ticker in snapshots)
    if not symbols:
        raise ValueError("No stock history available")
    stocks = pd.concat([snapshots[ticker] for ticker in symbols], ignore_index=True)
    stocks = stocks.sort_values(["timestamp", "ticker"]).reset_index(drop=True)
    stocks.attrs = {}
    signals = build_signals(build_features(stocks, benchmark=spy), **config["signal_parameters"])
    ledgers = {name: [] for name in ("events", "eligible", "non_signal", "trades", "observations")}
    for _, fold in folds.iterrows():
        print(f"Evaluating fold {fold.fold}", file=sys.stderr, flush=True)
        result = evaluate_fold(signals, spy, fold, requested, horizons=config["horizons"],
                               barrier_parameters=config["barrier_parameters"])
        for name in ledgers:
            ledgers[name].append(result[name])
    tables = {name: pd.concat(parts, ignore_index=True) for name, parts in ledgers.items()}
    summaries, concentration = summarize_robustness(tables, requested, uncertainty=config["uncertainty"])
    # Explicit zero exposure for missing/pre-inception ticker-folds, not fabricated bars.
    index = pd.MultiIndex.from_product([folds.fold, requested], names=["fold", "ticker"])
    frequency = summaries["frequency"].set_index(["fold", "ticker"]).reindex(index)
    counts = ["observed", "eligible", "ready", "conditions", "events"]
    frequency[counts] = frequency[counts].fillna(0).astype(int)
    summaries["frequency"] = frequency.reset_index()
    exclusions = []
    for row in summaries["frequency"].itertuples():
        if row.ready == 0:
            exclusions.append({"ticker": row.ticker, "fold": row.fold, "reason": "no_ready_oos_observations",
                               "detail": "No cached bars in fold or insufficient causal feature/threshold history"})
    usable = sorted(summaries["frequency"].loc[summaries["frequency"].ready > 0, "ticker"].unique())
    for ticker in symbols:
        if ticker not in usable:
            exclusions.append({"ticker": ticker, "fold": "all", "reason": "insufficient_history",
                               "detail": "No ready OOS observations in any fold; zero-event stocks are not excluded"})
    for selection in ("events", "eligible", "non_signal"):
        summaries[selection + "_status_counts"] = tables[selection].groupby(
            ["fold", "horizon", "status"], sort=True).size().rename("count").reset_index()
    summaries["folds"] = folds
    metadata = {"requested_tickers": requested, "requested_count": len(requested),
                "usable_tickers": usable, "usable_count": len(usable),
                "excluded_count": len(requested) - len(usable), "folds": folds.to_dict("records"),
                "concentration": concentration, "feature_parameters": signals.attrs["feature_parameters"],
                "signal_parameters": signals.attrs["signal_parameters"]}
    return tables | summaries, metadata, exclusions


def run_experiment(*, cache_dir: Path = DEFAULT_CACHE_DIR, output_dir: Path = ROOT / "results" / "exp_002",
                   download: bool = False, prepare_only: bool = False, config_path: Path = CONFIG) -> dict:
    """Acquire optional missing caches, then evaluate under a provider-download guard."""
    config = load_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    if download:
        snapshots, exclusions, provenance = acquire_data(config, Path(cache_dir), download=True)
    else:
        with patch("yfinance.download", side_effect=AssertionError("Offline EXP-002 cannot download")):
            snapshots, exclusions, provenance = acquire_data(config, Path(cache_dir))
    if prepare_only:
        result = {"snapshots": provenance, "exclusions": exclusions}
        write_json(output_dir / "acquisition.json", result)
        return json_safe(result)
    with patch("yfinance.download", side_effect=AssertionError("Outcome evaluation must remain offline")):
        artifacts, result, history_exclusions = evaluate_snapshots(snapshots, config)
    exclusions.extend(history_exclusions)
    exclusions.extend({"ticker": ticker, "fold": "all", "reason": "previously_inspected_issuer",
                       "detail": "GOOG shares GOOGL issuer" if ticker == "GOOG" else "EXP-001 stock"}
                      for ticker in config["excluded_tickers"] if ticker in config["source_tickers"])
    artifacts["exclusions"] = pd.DataFrame(exclusions, columns=["ticker", "fold", "reason", "detail"])
    hashes = {}
    for name, frame in artifacts.items():
        frame = frame.copy()
        frame.attrs = {}
        if name in ("events", "eligible", "non_signal", "trades", "observations"):
            path = output_dir / f"{name}.parquet"
            frame.to_parquet(path, index=False, compression="zstd")
        else:
            path = output_dir / f"{name}.csv"
            frame.to_csv(path, index=False, float_format="%.17g", lineterminator="\n")
        hashes[path.name] = sha256(path.read_bytes()).hexdigest()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, check=True,
                               capture_output=True, text=True).stdout.strip())
    result.update(experiment="EXP-002", config=config, preregistration_commit=PREREGISTRATION,
                  config_sha256=sha256(config_path.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
                  code_commit=revision, working_tree_dirty=dirty, snapshots=provenance,
                  execution_source_sha256={name: sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                      for name in ("src/data.py", "src/features.py", "src/signals.py", "src/backtest.py",
                                   "src/metrics.py", "src/universe.py", "src/walkforward.py",
                                   "src/robustness.py", "scripts/evaluate_exp002.py")},
                  artifact_sha256=hashes, environment={"python": platform.python_version(),
                      "numpy": np.__version__, "pandas": pd.__version__},
                  interpretation="static survivor-biased cross-sectional evidence; not fresh temporal holdout")
    write_json(output_dir / "metadata.json", result)
    return json_safe(result)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "exp_002")
    parser.add_argument("--download", action="store_true", help="Download missing symbols only, never refresh")
    parser.add_argument("--prepare-only", action="store_true", help="Cache/coverage audit without outcomes")
    args = parser.parse_args()
    result = run_experiment(**vars(args))
    print(json.dumps({key: result[key] for key in ("requested_count", "usable_count", "excluded_count")
                      if key in result}, indent=2))


if __name__ == "__main__":
    main()
