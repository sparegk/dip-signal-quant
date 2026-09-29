"""Reproduce EXP-001 offline: python -m scripts.evaluate_v1 [--cache-dir PATH].

Print JSON only; do not download, refresh snapshots, save data, or tune parameters.
All research settings are fixed here before examining results.
"""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.backtest import assign_research_splits, compute_forward_outcomes, simulate_barrier_trades
from src.data import DEFAULT_CACHE_DIR, load_parquet
from src.features import build_features
from src.metrics import summarize_outcomes, trade_metrics
from src.signals import build_signals


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


def run_experiment(cache_dir: str | Path = DEFAULT_CACHE_DIR) -> dict:
    """Fixed V1, all five horizons, common 60/20/20 splits; no outcome selection."""
    symbols = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL")
    directory = Path(cache_dir)
    with patch("yfinance.download", side_effect=AssertionError("EXP-001 must remain offline")):
        snapshots = {symbol: load_parquet(directory / f"{symbol}.parquet", ticker=symbol)
                     for symbol in (*symbols, "SPY")}
        provenance = {
            symbol: {"sha256": sha256((directory / f"{symbol}.parquet").read_bytes()).hexdigest(),
                     "rows": len(frame), "start": str(frame.timestamp.min().date()),
                     "end": str(frame.timestamp.max().date()), "source": frame.attrs}
            for symbol, frame in snapshots.items()
        }
        stocks = pd.concat([snapshots[s] for s in symbols], ignore_index=True).sort_values(
            ["timestamp", "ticker"]
        ).reset_index(drop=True)
        stocks.attrs = {"snapshots": {s: snapshots[s].attrs for s in symbols}}
        signals = build_signals(build_features(stocks, benchmark=snapshots["SPY"]))
        split = assign_research_splits(signals)
        original = signals.copy(deep=True)
        outcomes = {
            selection: compute_forward_outcomes(split, selection=selection, benchmark=snapshots["SPY"])
            for selection in ("events", "eligible", "non_signal")
        }
        # Per-side 1 bp commission + 5 bp slippage; gross columns are the zero-cost case.
        cost_assumptions = {"commission_rate": .0001, "slippage_rate": .0005}
        independent = simulate_barrier_trades(split, **cost_assumptions)
        stream = simulate_barrier_trades(split, mode="non_overlapping", **cost_assumptions)
        pd.testing.assert_frame_equal(signals, original, check_exact=True)
    summaries = {name: summarize_outcomes(frame).to_dict("records") for name, frame in outcomes.items()}
    components = summarize_outcomes(
        outcomes["events"].loc[outcomes["events"].horizon == 10],
        group_by=("split", "horizon", "dip_component_count"),
    ).to_dict("records")
    trade_summary, per_ticker, dates = [], [], []
    for label, group in split.groupby("split", sort=False):
        dates.append({"split": label, "start": str(group.timestamp.min().date()),
                      "end": str(group.timestamp.max().date()), "rows": len(group),
                      "eligible": int(group.dip_ready_v1.sum()), "events": int(group.dip_event_v1.sum())})
        for mode, table in (("independent", independent), ("non_overlapping", stream)):
            selected = table.loc[table["split"] == label]
            trade_summary.append({"split": label, "mode": mode,
                                  "statuses": selected.status.value_counts().to_dict(),
                                  "ambiguous_exits": int(selected.ambiguous_bar.sum()),
                                  **trade_metrics(selected)})
        for ticker in symbols:
            selected = stream.loc[(stream["split"] == label) & (stream.ticker == ticker)]
            per_ticker.append({"split": label, "ticker": ticker, **trade_metrics(selected, sequential=True)})
    repository = Path(__file__).resolve().parents[1]
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repository, check=True,
                              text=True, capture_output=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=repository, check=True,
                               text=True, capture_output=True).stdout.strip())
    return _json_safe({
        "experiment": "EXP-001", "code_commit": revision, "working_tree_dirty": dirty,
        "environment": {"python": platform.python_version(), "pandas": pd.__version__, "numpy": np.__version__},
        "snapshots": provenance, "splits": dates, "split_parameters": split.attrs["research_splits"],
        "signal_parameters": signals.attrs["signal_parameters"],
        "exit_parameters": independent.attrs["evaluation_parameters"],
        "uncertainty": {"confidence": .95, "seed": 42, "n_bootstrap": 2000,
                        "block_size_event_dates": 20, "method": "circular_date_cluster_blocks"},
        "forward_summaries": summaries, "component_10d": components,
        "trade_summaries": trade_summary, "per_ticker_non_overlapping": per_ticker,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    args = parser.parse_args()
    print(json.dumps(run_experiment(args.cache_dir), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
