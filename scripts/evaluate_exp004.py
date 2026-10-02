"""Offline registered exit-policy walk-forward research on preserved EXP-002 inputs."""

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
import sys
from unittest.mock import patch

import numpy as np
import pandas as pd

from scripts.evaluate_exp002 import acquire_data, json_safe, load_config as exp002_config, write_json
from src.data import DEFAULT_CACHE_DIR
from src.exit_policies import candidate_catalog, evaluate_exit_policies
from src.features import build_features
from src.paper_archive import verify_run
from src.signals import build_signals
from src.walkforward import annual_folds


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/exp004.json"
PREREGISTRATION = "55a4c5b"
REGISTERED_CONFIG_SHA256 = "b01cd9855668d0dcbe75e576d316bcca2215007462df25b0f796ea51e22e6c8a"


def load_config(path: Path = CONFIG) -> dict:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    if sha256(raw).hexdigest() != REGISTERED_CONFIG_SHA256:
        raise ValueError("EXP-004 registered configuration changed")
    config = json.loads(raw)
    candidate_catalog(config)
    for name, expected in config["frozen_source_sha256"].items():
        if sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest() != expected:
            raise ValueError(f"Frozen V1 source changed: {name}")
    return config


def load_frozen_signals(config: dict, *, cache_dir: Path, source_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Verify original vintages/exclusions; use existing ingestion and V1 only."""
    metadata_path = source_dir / "metadata.json"
    if sha256(metadata_path.read_bytes()).hexdigest() != config["source_metadata_sha256"]:
        raise ValueError("EXP-002 metadata vintage changed")
    original = json.loads(metadata_path.read_text(encoding="utf-8"))
    for name, expected in original["artifact_sha256"].items():
        if sha256((source_dir / name).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Frozen EXP-002 artifact changed: {name}")
    source_config = ROOT / "config/exp002.json"
    if sha256(source_config.read_bytes().replace(b"\r\n", b"\n")).hexdigest() != config["source_config_sha256"]:
        raise ValueError("EXP-002 configuration changed")
    source = exp002_config(source_config)
    for ticker, snapshot in original["snapshots"].items():
        if sha256((cache_dir / f"{ticker}.parquet").read_bytes()).hexdigest() != snapshot["sha256"]:
            raise ValueError(f"Frozen input vintage changed: {ticker}")
    with patch("yfinance.download", side_effect=AssertionError("EXP-004 is offline")):
        snapshots, exclusions, provenance = acquire_data(source, cache_dir)
    usable = original["usable_tickers"]
    if set(snapshots) != set(usable) | {source["benchmark"]}:
        raise ValueError("Frozen usable universe changed")
    stocks = pd.concat([snapshots[ticker] for ticker in usable], ignore_index=True)
    stocks = stocks.sort_values(["timestamp", "ticker"]).reset_index(drop=True)
    stocks.attrs = {}
    spy = snapshots[source["benchmark"]]
    signals = build_signals(build_features(stocks, benchmark=spy), **config["signal_parameters"])
    folds = annual_folds(spy.timestamp, initial_history_years=config["walkforward"]["initial_history_years"])
    expected = pd.read_parquet(source_dir / "events.parquet")
    keys = ["timestamp", "ticker", "dip_component_count"]
    expected = expected[keys].drop_duplicates().sort_values(keys).reset_index(drop=True)
    actual = signals.loc[signals.dip_event_v1 & signals.timestamp.between(
        folds.test_start.min(), folds.test_end.max()), keys].sort_values(keys).reset_index(drop=True)
    pd.testing.assert_frame_equal(actual, expected, check_dtype=False)
    return signals, folds, dict(requested_count=original["requested_count"], usable_count=len(usable),
                               usable_tickers=usable, exclusions=exclusions, snapshots=provenance,
                               verified_oos_event_count=len(actual))


def diagnostic_summaries(oos: pd.DataFrame) -> pd.DataFrame:
    rows = []
    levels = [("ALL", oos), *oos.groupby("fold", sort=True)]
    for fold, part in levels:
        for (policy, mode), group in part.groupby(["policy", "mode"], sort=True):
            complete = group.loc[group.status.eq("completed")]
            row = dict(fold=fold, policy=policy, mode=mode, completed=len(complete),
                mean_full_window_mfe=complete.full_window_mfe.mean(),
                mean_full_window_mae=complete.full_window_mae.mean(),
                mean_capture=complete.mfe_capture.mean(), median_capture=complete.mfe_capture.median(),
                capture_count=int(complete.mfe_capture.notna().sum()),
                mean_remaining_mfe=complete.remaining_mfe.mean(),
                stopped_count=int(complete.exit_reason.eq("stop_loss").sum()))
            for threshold in (2, 5, 10):
                values = complete[f"stopped_recovered_{threshold}pct"].dropna()
                row[f"recovery_{threshold}pct_measurable_stops"] = len(values)
                row[f"recovery_{threshold}pct_count"] = int(values.sum())
                row[f"recovery_{threshold}pct_rate"] = values.mean()
            rows.append(row)
    return pd.DataFrame(rows)


def prospective_status(root: Path = ROOT / "data/paper_archive") -> dict:
    counts = Counter()
    for path in sorted((root / "runs").glob("*/receipt.json")):
        receipt = verify_run(root, path.parent.name)
        counts.update(receipt["classifications"].values())
    return dict(classification_counts=dict(counts),
                outcome_records=0, status="Prospective evaluation pending genuine paper-signal outcomes.")


def run_experiment(*, cache_dir: Path = DEFAULT_CACHE_DIR,
                   source_dir: Path = ROOT / "results/exp_002",
                   output_dir: Path = ROOT / "results/exp_004", config_path: Path = CONFIG) -> dict:
    """Generate deterministic artifacts; refuse output into preserved inputs."""
    config = load_config(config_path)
    output = output_dir.resolve()
    protected = [cache_dir.resolve(), source_dir.resolve(), (ROOT / "data").resolve()]
    if any(output == p or output in p.parents or p in output.parents for p in protected):
        raise ValueError("Output directory overlaps preserved inputs")
    signals, folds, metadata = load_frozen_signals(config, cache_dir=cache_dir, source_dir=source_dir)
    tables = evaluate_exit_policies(signals, folds, config,
                                   progress=lambda message: print(message, file=sys.stderr, flush=True))
    tables["fixed_control_results"] = tables["oos_results"].loc[tables["oos_results"].family.eq("control")].copy()
    tables["exit_efficiency"] = diagnostic_summaries(tables["oos_results"])
    tables["candidate_catalogue"] = pd.DataFrame(config["candidates"])
    output.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, frame in tables.items():
        frame = frame.copy()
        frame.attrs = {}
        if name in ("selected_policy_by_fold", "folds", "aggregate_summary", "fold_summary", "paired_uncertainty", "parameter_plateaus", "exit_efficiency", "candidate_catalogue"):
            path = output / f"{name}.csv"
            frame.to_csv(path, index=False, float_format="%.17g", lineterminator="\n")
        else:
            path = output / f"{name}.parquet"
            frame.to_parquet(path, index=False, compression="zstd")
        hashes[path.name] = sha256(path.read_bytes()).hexdigest()
    def git(*args):
        return subprocess.run(["git", *args], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    metadata.update(experiment="EXP-004", preregistration_commit=PREREGISTRATION,
        config_sha256=REGISTERED_CONFIG_SHA256, config=config,
        code_commit=git("rev-parse", "HEAD"), working_tree_dirty=bool(git("status", "--porcelain")),
        candidate_count=config["candidate_count"], selectable_candidate_count=config["selectable_candidate_count"],
        family_count=config["family_count"], fold_count=len(folds), artifact_sha256=hashes,
        execution_source_sha256={name: sha256((ROOT / name).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
            for name in ("src/backtest.py", "src/exit_policies.py", "src/metrics.py", "src/walkforward.py", "scripts/evaluate_exp004.py")},
        prospective=prospective_status(), environment=dict(python=platform.python_version(), numpy=np.__version__, pandas=pd.__version__),
        interpretation=config["walkforward"]["classification"])
    write_json(output / "metadata.json", metadata)
    return json_safe(metadata)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "results/exp_002")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results/exp_004")
    result = run_experiment(**vars(parser.parse_args()))
    print(json.dumps({key: result[key] for key in ("candidate_count", "usable_count", "fold_count", "prospective")}, indent=2))


if __name__ == "__main__":
    main()
