"""Descriptive research metrics; overlapping events are not portfolio returns."""

from collections.abc import Iterable
from numbers import Integral, Real

import numpy as np
import pandas as pd


def _values(values: Iterable[float]) -> np.ndarray:
    series = pd.Series(values)
    if series.empty:
        return np.empty(0, dtype=float)
    if (not pd.api.types.is_numeric_dtype(series.dtype)
            or pd.api.types.is_bool_dtype(series.dtype) or pd.api.types.is_complex_dtype(series.dtype)):
        raise ValueError("Returns must be real numeric values or NaN")
    result = series.to_numpy(dtype=float, na_value=np.nan)
    if np.isinf(result).any():
        raise ValueError("Infinite returns are invalid")
    return result


def _integer(value: int, name: str, minimum: int = 1) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return int(value)


def _finite(value: float, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real) or not np.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def summarize_returns(
    returns: Iterable[float], *, dates: Iterable | None = None, confidence: float = .95,
    n_bootstrap: int = 2000, block_size: int = 1, seed: int = 42,
) -> dict[str, float | int]:
    """Return moments and seeded circular moving-block bootstrap uncertainty.

    With dates, keep all observations on each date together, then resample blocks
    of consecutive distinct observed dates. Blocks count EVENT dates, not exchange
    sessions. Require >=2*block_size clusters for SE/CI; otherwise leave NaN. Without
    dates, each observation is a cluster; block_size=1 is the explicit IID special
    case, inappropriate for inference on overlapping outcomes. Mean is row-weighted.
    """
    level = _finite(confidence, "confidence")
    if not 0 < level < 1:
        raise ValueError("confidence must lie strictly between zero and one")
    draws = _integer(n_bootstrap, "n_bootstrap", 2)
    block = _integer(block_size, "block_size")
    random_seed = _integer(seed, "seed", 0)
    raw = _values(returns)
    mask = ~np.isnan(raw)
    values = raw[mask]
    if dates is None:
        labels = np.arange(len(values))
    else:
        supplied = pd.Series(dates)
        if (len(supplied) != len(raw) or not pd.api.types.is_datetime64_dtype(supplied.dtype)
                or supplied.isna().any() or not supplied.is_monotonic_increasing
                or not supplied.eq(supplied.dt.normalize()).all()):
            raise ValueError("dates must be aligned, sorted, naive midnight timestamps")
        labels = pd.factorize(supplied.to_numpy()[mask], sort=True)[0]
    n = len(values)
    summary = {"count": n, "missing_count": int((~mask).sum()), "mean": np.nan,
               "median": np.nan, "std": np.nan, "standard_error": np.nan,
               "ci_lower": np.nan, "ci_upper": np.nan, "win_rate": np.nan,
               "expectancy": np.nan, "profit_factor": np.nan, "cluster_count": 0}
    if not n:
        return summary
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        mean = float(values.mean())
        losses = -values[values < 0].sum()
        summary.update(mean=mean, median=float(np.median(values)),
                       std=float(values.std(ddof=1)) if n > 1 else np.nan,
                       win_rate=float((values > 0).mean()), expectancy=mean,
                       profit_factor=float(values[values > 0].sum() / losses) if losses > 0 else np.nan)
        sums = np.bincount(labels, weights=values)
        counts = np.bincount(labels)
        clusters = len(sums)
        summary["cluster_count"] = clusters
        if clusters < 2 * block:
            return summary
        rng = np.random.default_rng(random_seed)
        means = np.empty(draws)
        # Batches bound allocation for larger unconditional control samples.
        for offset in range(0, draws, 128):
            size = min(128, draws - offset)
            starts = rng.integers(0, clusters, size=(size, (clusters + block - 1) // block))
            indices = (starts[:, :, None] + np.arange(block)) % clusters
            indices = indices.reshape(size, -1)[:, :clusters]
            means[offset:offset + size] = sums[indices].sum(axis=1) / counts[indices].sum(axis=1)
        summary.update(standard_error=float(means.std(ddof=1)),
                       ci_lower=float(np.quantile(means, (1 - level) / 2)),
                       ci_upper=float(np.quantile(means, (1 + level) / 2)))
    return summary


def risk_adjusted_metrics(
    period_returns: Iterable[float], *, periods_per_year: float = 252,
    risk_free_per_period: float = 0, target_per_period: float = 0,
) -> dict[str, float]:
    """Sharpe/Sortino for an EXPLICIT regular-period non-overlapping return series.

    Never pass pooled events or irregular-duration trades. Caller establishes the
    frequency and capital accounting. No frequency inference or annualization of
    variable-holding trade returns is performed. Zero risk/short samples => NaN.
    """
    scale = _finite(periods_per_year, "periods_per_year")
    risk_free = _finite(risk_free_per_period, "risk_free_per_period")
    target = _finite(target_per_period, "target_per_period")
    if scale <= 0:
        raise ValueError("periods_per_year must be positive")
    values = _values(period_returns)
    if np.isnan(values).any() or (values < -1).any():
        raise ValueError("Regular-period returns must be complete and >= -1")
    if len(values) < 2:
        return {"sharpe": np.nan, "sortino": np.nan}
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        std = float(np.std(values - risk_free, ddof=1))
        downside = float(np.sqrt(np.mean(np.minimum(values - target, 0) ** 2)))
        return {"sharpe": float(np.mean(values - risk_free) / std * np.sqrt(scale)) if std > 0 else np.nan,
                "sortino": float(np.mean(values - target) / downside * np.sqrt(scale)) if downside > 0 else np.nan}


def sequential_return_metrics(returns: Iterable[float]) -> dict[str, float]:
    """Hypothetical fully reinvested, non-overlapping sequential returns.

    Include initial wealth=1 in drawdown, so a first-trade loss is not hidden.
    This is close-of-trade drawdown, not daily mark-to-market portfolio drawdown.
    """
    values = _values(returns)
    if np.isnan(values).any() or (values <= -1).any():
        raise ValueError("Sequential returns must be complete and greater than -1")
    if not len(values):
        return {"cumulative_return": np.nan, "maximum_drawdown": np.nan}
    with np.errstate(over="raise", invalid="raise", divide="raise"):
        wealth = np.r_[1.0, np.cumprod(1 + values)]
        if not np.isfinite(wealth).all() or (wealth <= 0).any():
            raise ValueError("Numerical overflow/underflow in compounded wealth")
        drawdown = wealth / np.maximum.accumulate(wealth) - 1
    return {"cumulative_return": float(wealth[-1] - 1), "maximum_drawdown": float(drawdown.min())}


def summarize_outcomes(
    outcomes: pd.DataFrame, *, group_by: tuple[str, ...] = ("split", "horizon"),
    block_size: int = 20, n_bootstrap: int = 2000, seed: int = 42,
) -> pd.DataFrame:
    """Descriptive outcome groups, bootstrap intervals, and PAIRED benchmark means."""
    required = {*group_by, "timestamp", "status", "forward_return", "mfe", "mae", "benchmark_return"}
    if not outcomes.columns.is_unique or not required.issubset(outcomes.columns) or not group_by:
        raise ValueError("Missing/duplicate outcome columns or empty grouping")
    if not outcomes.status.isin(("completed", "no_next_bar", "incomplete_window", "split_boundary")).all():
        raise ValueError("Unknown outcome status")
    completed = outcomes.loc[outcomes.status == "completed"]
    for column in ("forward_return", "mfe", "mae"):
        if np.isnan(_values(completed[column])).any():
            raise ValueError("Completed outcomes cannot contain missing measurements")
    _values(completed.benchmark_return)  # Benchmark absence is allowed, infinity is not.
    rows = []
    for key, group in outcomes.groupby(list(group_by), sort=True, observed=True, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        valid = group.loc[group.status == "completed"].sort_values("timestamp")
        stats = summarize_returns(valid.forward_return, dates=valid.timestamp,
                                  block_size=block_size, n_bootstrap=n_bootstrap, seed=seed)
        paired = valid.loc[valid.benchmark_return.notna()]
        rows.append(dict(zip(group_by, key)) | stats | {
            "observations": len(group), "excluded": len(group) - len(valid),
            "average_mfe": valid.mfe.mean(), "average_mae": valid.mae.mean(),
            "benchmark_count": len(paired), "paired_stock_mean": paired.forward_return.mean(),
            "benchmark_mean": paired.benchmark_return.mean(),
            "mean_excess_return": (paired.forward_return - paired.benchmark_return).mean(),
        })
    return pd.DataFrame(rows)


def trade_metrics(trades: pd.DataFrame, *, sequential: bool = False) -> dict[str, float | int]:
    """Summarize completed trades, retaining candidate/exclusion counts.

    sequential=True requires a single ticker's sorted strictly non-overlapping
    trades. Compounding assumes full reinvestment and zero idle-cash return. Pooled
    streams never get a made-up equity curve, Sharpe, Sortino, or drawdown.
    """
    required = {"status", "ticker", "entry_timestamp", "exit_timestamp", "net_return",
                "gross_return", "mfe", "mae", "holding_bars", "exit_reason"}
    if not isinstance(sequential, bool) or not trades.columns.is_unique or not required.issubset(trades):
        raise ValueError("Malformed trade schema or sequential flag")
    if not trades.status.isin(("completed", "overlap", "no_next_bar", "incomplete_window", "split_boundary")).all():
        raise ValueError("Unknown trade status")
    complete = trades.loc[trades.status == "completed"]
    numeric = ("net_return", "gross_return", "mfe", "mae", "holding_bars")
    for column in numeric:
        if np.isnan(_values(complete[column])).any():
            raise ValueError("Completed trades cannot contain missing metrics")
    if not complete.exit_reason.isin(("take_profit", "stop_loss", "time_exit")).all():
        raise ValueError("Invalid completed exit reason")
    for column in ("entry_timestamp", "exit_timestamp"):
        if len(complete) and (not pd.api.types.is_datetime64_dtype(complete[column].dtype)
                             or complete[column].isna().any()
                             or not complete[column].eq(complete[column].dt.normalize()).all()):
            raise ValueError("Completed trades need valid session timestamps")
    if (complete.exit_timestamp < complete.entry_timestamp).any():
        raise ValueError("Exit cannot precede entry")
    if ((complete.holding_bars < 1).any() or (complete.holding_bars % 1 != 0).any()
            or (complete.net_return <= -1).any() or (complete.gross_return <= -1).any()
            or (complete.mfe < 0).any() or (complete.mae > 0).any()):
        raise ValueError("Invalid completed trade metrics")
    # Bootstrap uncertainty is for forward outcome analysis; do not imply that
    # irregular trades are an equally spaced independent return series.
    returns = complete.net_return.to_numpy(dtype=float)
    n = len(returns)
    losses = -returns[returns < 0].sum()
    wins = returns[returns > 0]
    losing_returns = returns[returns < 0]
    win_probability = len(wins) / n if n else np.nan
    loss_probability = len(losing_returns) / n if n else np.nan
    average_win = float(wins.mean()) if len(wins) else np.nan
    average_loss = float(losing_returns.mean()) if len(losing_returns) else np.nan
    # The arithmetic decomposition is algebraically equal; use the direct sample
    # mean as canonical EV to avoid a roundoff-only mismatch with expectancy.
    expected_value = float(returns.mean()) if n else np.nan
    break_even_win_rate = (abs(average_loss) / (average_win + abs(average_loss))
                           if len(wins) and len(losing_returns) else np.nan)
    result = {"candidate_count": len(trades), "trade_count": n, "excluded_count": len(trades) - n,
              "win_rate": float((returns > 0).mean()) if n else np.nan,
              "win_probability": win_probability, "loss_probability": loss_probability,
              "average_win": average_win, "average_loss": average_loss,
              "average_return": float(returns.mean()) if n else np.nan,
              "median_return": float(np.median(returns)) if n else np.nan,
              "std": float(returns.std(ddof=1)) if n > 1 else np.nan,
              "expectancy": expected_value, "expected_value": expected_value,
              "break_even_win_rate": break_even_win_rate,
              "average_gross_return": complete.gross_return.mean(),
              "average_mfe": complete.mfe.mean(), "average_mae": complete.mae.mean(),
              "average_holding_bars": complete.holding_bars.mean(),
              "take_profit_rate": complete.exit_reason.eq("take_profit").mean(),
              "stop_loss_rate": complete.exit_reason.eq("stop_loss").mean(),
              "time_exit_rate": complete.exit_reason.eq("time_exit").mean(),
              "profit_factor": float(returns[returns > 0].sum() / losses) if losses > 0 else np.nan,
              "cumulative_return": np.nan, "maximum_drawdown": np.nan,
              "sharpe": np.nan, "sortino": np.nan}
    if sequential and n:
        if (complete.ticker.nunique() != 1 or not complete.entry_timestamp.is_monotonic_increasing
                or (complete.entry_timestamp.to_numpy()[1:] <= complete.exit_timestamp.to_numpy()[:-1]).any()):
            raise ValueError("Sequential metrics require one sorted non-overlapping ticker")
        result.update(sequential_return_metrics(returns))
    return result
