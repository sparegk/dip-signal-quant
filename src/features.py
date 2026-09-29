"""Trailing daily measurements available after the current session's close.

Windows count observed bars per ticker, not calendar days. No filling, thresholds,
labels, or execution logic. Later execution must respect availability (usually
t+1 or later). See docs/FEATURES.md for definitions and data-vintage limitations.
"""

from collections.abc import Callable, Iterable
from copy import deepcopy
from numbers import Integral, Real

import numpy as np
import pandas as pd

from src.data import validate_data


FeatureValues = dict[str, pd.Series]


def _windows(windows: Iterable[int], *, minimum: int = 1) -> tuple[int, ...]:
    """Validate window sizes and return unique sizes in ascending order."""
    values = tuple(windows)
    if not values or any(
        isinstance(n, (bool, np.bool_)) or not isinstance(n, Integral) or n < minimum
        for n in values
    ):
        raise ValueError(f"Windows must be nonempty integers >= {minimum}")
    return tuple(sorted(set(int(n) for n in values)))


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide by positive denominators; undefined denominators remain NaN."""
    top = numerator.to_numpy(dtype=np.float64)
    bottom = denominator.to_numpy(dtype=np.float64)
    if np.isinf(top).any() or np.isinf(bottom).any():
        raise ValueError("Numerical overflow in feature inputs")
    result = np.full(len(top), np.nan)
    np.divide(top, bottom, out=result, where=(bottom > 0) & ~np.isnan(top))
    return pd.Series(result, index=numerator.index)


def _moments(values: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """Full-window mean and sample std; reject undefined numerical results."""
    rolling = values.rolling(window, min_periods=window)
    mean, std = rolling.mean(), rolling.std(ddof=1)
    complete = rolling.count().eq(window)
    if not np.isfinite(mean[complete]).all() or not np.isfinite(std[complete]).all():
        raise ValueError("Numerical overflow in rolling moments")
    return mean, std


def _apply_by_ticker(
    data: pd.DataFrame,
    calculate: Callable[[pd.DataFrame], FeatureValues],
    *,
    preserve_input: bool = False,
) -> pd.DataFrame:
    """Validate once, isolate ticker histories, then restore canonical row order."""
    validate_data(data)
    base = data.reset_index(drop=True).copy()
    parts = []
    try:
        with np.errstate(over="raise", divide="raise", invalid="raise"):
            for _, group in base.groupby("ticker", sort=False, observed=True):
                values = calculate(group)
                parts.append(pd.DataFrame(values, index=group.index, dtype="float64"))
    except FloatingPointError as exc:
        raise ValueError("Numerical overflow or invalid feature arithmetic") from exc
    features = pd.concat(parts).sort_index()
    if np.isinf(features.to_numpy()).any():
        raise ValueError("Numerical overflow produced infinite features")
    retained = base if preserve_input else base[["timestamp", "ticker"]]
    overlap = set(retained.columns) & set(features.columns)
    if overlap:
        raise ValueError(f"Refusing to overwrite existing feature columns: {sorted(overlap)}")
    result = pd.concat([retained, features], axis=1)
    result.attrs = deepcopy(data.attrs)
    return result


def _returns(close: pd.Series, windows: tuple[int, ...]) -> FeatureValues:
    return {f"return_{n}d": _ratio(close, close.shift(n)) - 1 for n in windows}


def _locations(close: pd.Series, windows: tuple[int, ...]) -> FeatureValues:
    result = {}
    for n in windows:
        rolling = close.rolling(n, min_periods=n)
        distance_high = _ratio(close, rolling.max()) - 1
        result[f"drawdown_{n}d"] = distance_high
        result[f"distance_from_low_{n}d"] = _ratio(close, rolling.min()) - 1
        result[f"distance_from_high_{n}d"] = distance_high
    return result


def _zscores(close: pd.Series, windows: tuple[int, ...]) -> FeatureValues:
    result = {}
    for n in windows:
        mean, std = _moments(close, n)
        result[f"price_zscore_{n}d"] = _ratio(close - mean, std)
    return result


def _annualization(value: float) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError("annualization must be a finite positive number")
    if not np.isfinite(value) or value <= 0:
        raise ValueError("annualization must be a finite positive number")
    return float(value)


def _wilder(values: pd.Series, window: int) -> pd.Series:
    """Seed with the first n finite samples' mean, then recurse with alpha=1/n.

    Callers exclude the undefined initial price change/TR. pandas executes the
    recurrence in compiled code; no per-row Python loop or unseeded EMA shortcut.
    """
    if len(values) < window:
        return pd.Series(np.nan, index=values.index, dtype=float)
    seeded = values.iloc[window - 1:].copy()
    seeded.iloc[0] = values.iloc[:window].mean()
    if not np.isfinite(seeded.to_numpy()).all():
        raise ValueError("Numerical overflow in Wilder seed")
    return seeded.ewm(alpha=1 / window, adjust=False).mean().reindex(values.index)


def _rsi(close: pd.Series, window: int) -> FeatureValues:
    changes = close.diff().iloc[1:]
    gain = _wilder(changes.clip(lower=0), window)
    loss = _wilder((-changes).clip(lower=0), window)
    rsi = 100 * _ratio(gain, gain + loss)
    return {f"rsi_{window}": rsi.reindex(close.index)}


def _atr(group: pd.DataFrame, window: int) -> FeatureValues:
    high, low, close = (group[c].astype(float) for c in ("high", "low", "close"))
    previous = close.shift(1)
    ranges = np.maximum.reduce([
        (high - low).to_numpy(), (high - previous).abs().to_numpy(),
        (low - previous).abs().to_numpy(),
    ])
    true_range = pd.Series(ranges, index=group.index)
    atr = _wilder(true_range.iloc[1:], window).reindex(group.index)
    return {"true_range": true_range, f"atr_{window}": atr,
            f"atr_pct_{window}": _ratio(atr, close)}


def _volatility(
    daily_returns: pd.Series, windows: tuple[int, ...], annualization: float
) -> FeatureValues:
    return {f"volatility_{n}d": _moments(daily_returns, n)[1] * np.sqrt(annualization)
            for n in windows}


def _volume(volume: pd.Series, windows: tuple[int, ...]) -> FeatureValues:
    result = {}
    for n in windows:
        mean, std = _moments(volume, n)
        result[f"volume_mean_{n}d"] = mean
        result[f"relative_volume_{n}d"] = _ratio(volume, mean)
        result[f"volume_zscore_{n}d"] = _ratio(volume - mean, std)
    return result


def compute_returns(
    data: pd.DataFrame, windows: Iterable[int] = (1, 5, 10, 20)
) -> pd.DataFrame:
    """Identity plus close[t] / close[t-n] - 1, separately for each ticker."""
    sizes = _windows(windows)
    return _apply_by_ticker(data, lambda g: _returns(g["close"].astype(float), sizes))


def compute_price_location_features(
    data: pd.DataFrame, windows: Iterable[int] = (20, 60)
) -> pd.DataFrame:
    """Identity plus drawdown and low/high distances; extrema include today."""
    sizes = _windows(windows)
    return _apply_by_ticker(data, lambda g: _locations(g["close"].astype(float), sizes))


def compute_price_zscores(
    data: pd.DataFrame, windows: Iterable[int] = (20,)
) -> pd.DataFrame:
    """Identity plus trailing close z-scores, sample std (ddof=1); flat => NaN."""
    sizes = _windows(windows, minimum=2)
    return _apply_by_ticker(data, lambda g: _zscores(g["close"].astype(float), sizes))


def compute_rsi(data: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """Wilder RSI seeded by n changes; no gains/losses => NaN, loss-only => 0."""
    size = _windows((window,), minimum=2)[0]
    return _apply_by_ticker(data, lambda g: _rsi(g["close"].astype(float), size))


def compute_atr(data: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """True Range and mean-seeded Wilder ATR; first TR needs a previous close."""
    size = _windows((window,))[0]
    return _apply_by_ticker(data, lambda g: _atr(g, size))


def compute_volatility(
    data: pd.DataFrame, windows: Iterable[int] = (20, 60), *, annualization: float = 252
) -> pd.DataFrame:
    """Sample std of n trailing daily simple returns, scaled by sqrt(annualization)."""
    sizes = _windows(windows, minimum=2)
    scale = _annualization(annualization)
    return _apply_by_ticker(
        data, lambda g: _volatility(_returns(g["close"].astype(float), (1,))["return_1d"], sizes, scale)
    )


def compute_volume_features(
    data: pd.DataFrame, windows: Iterable[int] = (20,)
) -> pd.DataFrame:
    """Trailing mean volume, relative volume, and sample-std volume z-score."""
    sizes = _windows(windows, minimum=2)
    return _apply_by_ticker(data, lambda g: _volume(g["volume"].astype(float), sizes))


def build_features(
    data: pd.DataFrame,
    *,
    return_windows: Iterable[int] = (1, 5, 10, 20),
    location_windows: Iterable[int] = (20, 60),
    zscore_windows: Iterable[int] = (20,),
    rsi_window: int = 14,
    atr_window: int = 14,
    volatility_windows: Iterable[int] = (20, 60),
    volume_windows: Iterable[int] = (20,),
    annualization: float = 252,
) -> pd.DataFrame:
    """Copy validated OHLCV and append trailing measurements in canonical order.

    Preserve input columns and provenance, reset the row index, and reject column
    collisions. Full-window warm-up NaNs stay explicit. No network or file access.
    """
    returns = _windows(return_windows)
    locations = _windows(location_windows)
    zscores = _windows(zscore_windows, minimum=2)
    rsi = _windows((rsi_window,), minimum=2)[0]
    atr = _windows((atr_window,))[0]
    volatility = _windows(volatility_windows, minimum=2)
    volume = _windows(volume_windows, minimum=2)
    scale = _annualization(annualization)

    def calculate(group: pd.DataFrame) -> FeatureValues:
        close = group["close"].astype(float)
        price_returns = _returns(close, tuple(sorted(set(returns) | {1})))
        return {
            **{f"return_{n}d": price_returns[f"return_{n}d"] for n in returns},
            **_locations(close, locations), **_zscores(close, zscores),
            **_rsi(close, rsi), **_atr(group, atr),
            **_volatility(price_returns["return_1d"], volatility, scale),
            **_volume(group["volume"].astype(float), volume),
        }

    return _apply_by_ticker(data, calculate, preserve_input=True)
