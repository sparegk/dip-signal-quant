"""Trailing daily measurements available after the current session's close.

Windows count observed bars per ticker, not calendar days. No filling, thresholds,
labels, or execution logic. Later execution must respect availability (usually
t+1 or later). See docs/FEATURES.md for definitions and data-vintage limitations.
"""

from collections.abc import Callable, Iterable
from copy import deepcopy
from numbers import Integral

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


def build_features(
    data: pd.DataFrame,
    *,
    return_windows: Iterable[int] = (1, 5, 10, 20),
    location_windows: Iterable[int] = (20, 60),
    zscore_windows: Iterable[int] = (20,),
) -> pd.DataFrame:
    """Copy validated OHLCV and append trailing measurements in canonical order.

    Preserve input columns and provenance, reset the row index, and reject column
    collisions. Full-window warm-up NaNs stay explicit. No network or file access.
    """
    returns = _windows(return_windows)
    locations = _windows(location_windows)
    zscores = _windows(zscore_windows, minimum=2)

    def calculate(group: pd.DataFrame) -> FeatureValues:
        close = group["close"].astype(float)
        return {**_returns(close, returns), **_locations(close, locations),
                **_zscores(close, zscores)}

    return _apply_by_ticker(data, calculate, preserve_input=True)
