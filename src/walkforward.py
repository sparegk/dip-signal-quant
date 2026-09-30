"""Expanding calendar folds and frozen evaluations with complete-window censoring."""

from collections.abc import Iterable
from numbers import Integral

import numpy as np
import pandas as pd

from src.backtest import HORIZONS, compute_forward_outcomes, simulate_barrier_trades
from src.data import validate_data
from src.universe import membership_mask


def annual_folds(dates: Iterable[pd.Timestamp], *, initial_history_years: int = 4) -> pd.DataFrame:
    """Use full calendar OOS years after an initial history; retain a partial last year."""
    calendar = pd.DatetimeIndex(dates)
    if (calendar.empty or calendar.hasnans or calendar.tz is not None
            or not calendar.is_unique or not calendar.is_monotonic_increasing
            or not calendar.equals(calendar.normalize())):
        raise ValueError("Fold calendar must be unique sorted naive midnight dates")
    if (isinstance(initial_history_years, bool) or not isinstance(initial_history_years, Integral)
            or initial_history_years < 1):
        raise ValueError("Initial history must be a positive integer number of years")
    anniversary = calendar[0] + pd.DateOffset(years=int(initial_history_years))
    first_year = anniversary.year + int((anniversary.month, anniversary.day) != (1, 1))
    rows = []
    for year in range(first_year, calendar[-1].year + 1):
        selected = calendar[calendar.year == year]
        if selected.empty:
            continue
        history = calendar[calendar < selected[0]]
        rows.append({"fold": str(year), "history_start": calendar[0], "history_end": history[-1],
                     "test_start": selected[0], "test_end": selected[-1],
                     "test_sessions": len(selected),
                     "partial_year": selected[-1] < pd.bdate_range(f"{year}-12-24", f"{year}-12-31")[-1]})
    if not rows:
        raise ValueError("No out-of-sample year after the initial history")
    result = pd.DataFrame(rows)
    validate_folds(result)
    return result


def validate_folds(folds: pd.DataFrame) -> None:
    """Reject overlap, backwards history, changing origins and nonexpanding order."""
    required = {"fold", "history_start", "history_end", "test_start", "test_end"}
    if (folds.empty or not folds.columns.is_unique or not required.issubset(folds)
            or folds.fold.isna().any() or folds.fold.duplicated().any()):
        raise ValueError("Invalid fold schema or identities")
    for column in required - {"fold"}:
        if (not pd.api.types.is_datetime64_dtype(folds[column]) or folds[column].isna().any()
                or not folds[column].eq(folds[column].dt.normalize()).all()):
            raise ValueError("Fold boundaries must be naive midnight timestamps")
    if (folds.history_start.nunique() != 1 or (folds.history_start > folds.history_end).any()
            or (folds.history_end >= folds.test_start).any()
            or (folds.test_start > folds.test_end).any()
            or not folds.test_start.is_monotonic_increasing
            or not folds.history_end.is_monotonic_increasing
            or (folds.test_start.to_numpy()[1:] <= folds.test_end.to_numpy()[:-1]).any()
            or (folds.history_end.to_numpy()[1:] < folds.test_end.to_numpy()[:-1]).any()):
        raise ValueError("Folds must have disjoint tests and expanding prior history")


def spy_regimes(benchmark: pd.DataFrame, *, window: int = 200) -> pd.DataFrame:
    """Signal-date completed SPY close versus its causal full trailing mean."""
    validate_data(benchmark)
    if benchmark.ticker.nunique() != 1 or benchmark.ticker.iloc[0] != "SPY":
        raise ValueError("Regime benchmark must be SPY only")
    if isinstance(window, bool) or not isinstance(window, Integral) or window < 1:
        raise ValueError("Regime window must be a positive integer")
    average = benchmark.close.rolling(int(window), min_periods=int(window)).mean()
    return pd.DataFrame({"timestamp": benchmark.timestamp,
                         "regime": np.where(average.isna(), "unknown",
                                            np.where(benchmark.close >= average, "above", "below"))})


def evaluate_fold(
    signals: pd.DataFrame, benchmark: pd.DataFrame, fold: pd.Series,
    universe: Iterable[str] | pd.DataFrame, *, horizons: Iterable[int] = HORIZONS,
    barrier_parameters: dict | None = None,
) -> dict[str, pd.DataFrame]:
    """Reuse V1 outcomes once for controls/events; truncate prices BEFORE evaluation.

    Input signals must be causal. Unchanged full-history signals are equivalent
    to expanding prefixes; later prices never enter this fold's outcome paths.
    Membership gates observations only and does not redefine V1 rising edges.
    """
    validate_data(signals)
    validate_folds(pd.DataFrame([fold]))
    base = signals.loc[signals.timestamp.between(fold.history_start, fold.test_end)].copy()
    reference = benchmark.loc[benchmark.timestamp.between(fold.history_start, fold.test_end)].copy()
    if base.empty or reference.empty:
        raise ValueError("Fold has no supplied history")
    base["member"] = membership_mask(base, universe)
    base = base.merge(spy_regimes(reference), on="timestamp", how="left", validate="many_to_one")
    base["regime"] = base.regime.fillna("unknown")
    base["fold"] = str(fold.fold)
    observation = base.loc[base.timestamp >= fold.test_start].reset_index(drop=True).copy()
    eligible = base.member & base.timestamp.ge(fold.test_start)
    for column in ("dip_ready_v1", "dip_condition_v1", "dip_event_v1"):
        base[column] &= eligible
    # One constant split; no bars after fold end exist for the evaluator to borrow.
    base["split"] = "test"
    controls = compute_forward_outcomes(base, horizons=horizons, selection="eligible", benchmark=reference)
    tags = base[["timestamp", "ticker", "dip_condition_v1", "dip_event_v1", "regime", "fold"]]
    controls = controls.merge(tags, on=["timestamp", "ticker"], how="left", validate="many_to_one")
    events = controls.loc[controls.dip_event_v1].reset_index(drop=True).copy()
    events["selection"] = "events"
    non_signal = controls.loc[~controls.dip_condition_v1].reset_index(drop=True).copy()
    non_signal["selection"] = "non_signal"
    ledgers = []
    for mode in ("independent", "non_overlapping"):
        trades = simulate_barrier_trades(base, mode=mode, **(barrier_parameters or {}))
        trades = trades.merge(tags, on=["timestamp", "ticker"], how="left", validate="many_to_one")
        trades["mode"] = mode
        ledgers.append(trades)
    return {"events": events, "eligible": controls, "non_signal": non_signal,
            "trades": pd.concat(ledgers, ignore_index=True), "observations": observation}
