"""DipSignal V1: prior-history-relative dip candidates, not trade instructions.

Feature values may include today's completed bar; percentile references must not.
Every threshold uses only previous same-ticker observations. No scoring, outcome
labels, position state, or trading logic. See docs/SIGNALS.md for the contract.
"""

from copy import deepcopy
from numbers import Integral, Real

import numpy as np
import pandas as pd

from src.data import normalize_ticker


FEATURE_COLUMNS = (
    "drawdown_60d", "price_zscore_20d", "distance_from_low_20d", "relative_return_10d",
)
THRESHOLD_COLUMNS = tuple(f"{feature}_threshold" for feature in FEATURE_COLUMNS)
COMPONENT_COLUMNS = (
    "dip_drawdown_component", "dip_price_zscore_component",
    "dip_low_proximity_component", "dip_relative_weakness_component",
)


def _integer(value: int, name: str, *, maximum: int | None = None) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    if maximum is not None and value > maximum:
        raise ValueError(f"{name} must be <= {maximum}")
    return int(value)


def _parameters(lookback: int, min_history: int, quantile: float) -> tuple[int, int, float]:
    lookback = _integer(lookback, "lookback")
    min_history = _integer(min_history, "min_history", maximum=lookback)
    if (isinstance(quantile, (bool, np.bool_)) or not isinstance(quantile, Real)
            or not np.isfinite(quantile) or not 0 <= quantile <= 1):
        raise ValueError("quantile must be a finite number in [0, 1]")
    return lookback, min_history, float(quantile)


def _validate_identity(data: pd.DataFrame) -> None:
    """Validate canonical identity without requiring unused raw OHLCV columns."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame")
    if not data.columns.is_unique:
        raise ValueError("Duplicate column labels are not allowed")
    missing = {"timestamp", "ticker"} - set(data.columns)
    if missing:
        raise ValueError(f"Missing identity columns: {sorted(missing)}")
    if data.empty:
        raise ValueError("Signal input must not be empty")
    if data[["timestamp", "ticker"]].isna().any().any():
        raise ValueError("Missing timestamp/ticker identity")
    timestamps = data["timestamp"]
    if not pd.api.types.is_datetime64_dtype(timestamps.dtype):
        raise ValueError("timestamp must be timezone-naive datetime64")
    if not timestamps.eq(timestamps.dt.normalize()).all():
        raise ValueError("timestamp must be a daily session date at midnight")
    if not all(isinstance(t, str) and normalize_ticker(t) == t for t in data["ticker"].unique()):
        raise ValueError("ticker values must be normalized strings")
    if data.duplicated(["ticker", "timestamp"]).any():
        raise ValueError("Duplicate ticker/timestamp observations")
    if not pd.MultiIndex.from_frame(data[["timestamp", "ticker"]]).is_monotonic_increasing:
        raise ValueError("Data must be sorted by timestamp, then ticker")


def _validate_features(data: pd.DataFrame) -> None:
    _validate_identity(data)
    missing = set(FEATURE_COLUMNS) - set(data.columns)
    if missing:
        raise ValueError(
            f"Missing required feature columns: {sorted(missing)}; "
            "supply benchmark-relative features rather than substituting values"
        )
    for column in FEATURE_COLUMNS:
        dtype = data[column].dtype
        if (not pd.api.types.is_numeric_dtype(dtype) or pd.api.types.is_bool_dtype(dtype)
                or pd.api.types.is_complex_dtype(dtype)):
            raise ValueError(f"{column} must contain real numeric values or NaN")
        if np.isinf(data[column].to_numpy(dtype=float, na_value=np.nan)).any():
            raise ValueError(f"{column} contains infinity")


def _thresholds(data: pd.DataFrame, lookback: int, min_history: int, quantile: float) -> pd.DataFrame:
    """Shift inside each group before rolling; never compress missing row slots."""
    parts = []
    for _, group in data.groupby("ticker", sort=False, observed=True):
        prior = group.loc[:, FEATURE_COLUMNS].astype(float).shift(1)
        rolling = prior.rolling(lookback, min_periods=min_history)
        thresholds = rolling.quantile(quantile, interpolation="linear")
        enough_history = rolling.count().ge(min_history)
        if (enough_history & ~np.isfinite(thresholds)).any().any():
            raise ValueError("Numerical overflow in historical quantile interpolation")
        thresholds.columns = THRESHOLD_COLUMNS
        parts.append(thresholds)
    return pd.concat(parts).sort_index()


def _record_parameters(
    output: pd.DataFrame, source: pd.DataFrame, lookback: int, min_history: int, quantile: float
) -> None:
    output.attrs = deepcopy(source.attrs)
    output.attrs["signal_parameters"] = {
        "version": "DipSignal V1", "lookback": lookback, "min_history": min_history,
        "quantile": quantile, "interpolation": "linear", "comparison": "<=",
        "reference": "prior_same_ticker_observed_bars", "availability": "after_close",
    }


def compute_historical_thresholds(
    data: pd.DataFrame, *, lookback: int = 252, min_history: int = 126, quantile: float = .20
) -> pd.DataFrame:
    """Identity plus four lower-tail thresholds from prior same-ticker features.

    Use the last lookback row positions before t; ignore NaNs within each feature's
    window but require min_history valid values there. Missing rows still occupy
    window positions. The current row never contributes to its own threshold.
    """
    lookback, min_history, quantile = _parameters(lookback, min_history, quantile)
    _validate_features(data)
    base = data.reset_index(drop=True)
    result = pd.concat([
        base[["timestamp", "ticker"]], _thresholds(base, lookback, min_history, quantile),
    ], axis=1)
    _record_parameters(result, data, lookback, min_history, quantile)
    return result


def compute_dip_components(
    data: pd.DataFrame, *, lookback: int = 252, min_history: int = 126, quantile: float = .20
) -> pd.DataFrame:
    """Return thresholds, four boolean components, and complete-row readiness.

    A component is True exactly when both operands exist and current <= threshold.
    Missing operands produce False, never an inferred dip. dip_ready_v1 requires
    all four current values and thresholds, regardless of the later count cutoff.
    """
    result = compute_historical_thresholds(
        data, lookback=lookback, min_history=min_history, quantile=quantile,
    )
    current = data.reset_index(drop=True).loc[:, FEATURE_COLUMNS].astype(float)
    thresholds = result.loc[:, THRESHOLD_COLUMNS].copy()
    thresholds.columns = FEATURE_COLUMNS
    available = current.notna() & thresholds.notna()
    flags = (available & current.le(thresholds)).astype(bool)
    flags.columns = COMPONENT_COLUMNS
    result = pd.concat([result, flags], axis=1)
    result["dip_ready_v1"] = available.all(axis=1).astype(bool)
    # concat's attribute handling is not a provenance contract.
    _record_parameters(result, data, int(lookback), int(min_history), float(quantile))
    return result


def _require_boolean(data: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        if column not in data:
            raise ValueError(f"Missing required boolean column: {column}")
        if not pd.api.types.is_bool_dtype(data[column].dtype) or data[column].isna().any():
            raise ValueError(f"{column} must be boolean without missing values")


def detect_dip_events(data: pd.DataFrame) -> pd.DataFrame:
    """Identity plus rising edges of dip_condition_v1 within each ticker.

    The first observed previous condition is False. Ineligible observations have
    condition=False, so they break a run; a later qualifying observation is a new
    observed event. This is neither position state nor a cooldown mechanism.
    """
    _validate_identity(data)
    _require_boolean(data, ("dip_condition_v1",))
    base = data.reset_index(drop=True)
    previous = base.groupby("ticker", sort=False, observed=True)["dip_condition_v1"].shift(
        1, fill_value=False,
    )
    result = base[["timestamp", "ticker"]].copy()
    result["dip_event_v1"] = base["dip_condition_v1"].astype(bool) & ~previous.astype(bool)
    result.attrs = deepcopy(data.attrs)
    return result


def build_signals(
    data: pd.DataFrame,
    *,
    lookback: int = 252,
    min_history: int = 126,
    quantile: float = .20,
    required_components: int = 3,
) -> pd.DataFrame:
    """Append transparent DipSignal V1 classifications to feature-engine output.

    Condition = complete-row readiness AND count >= required_components (1..4).
    Counts retain available component flags even on ineligible rows, but missing
    inputs/thresholds always prevent the condition and event. Preserve all input
    columns/provenance, reject output collisions, and never mutate input or fill
    features. No threshold optimization, scores, labels, or trade recommendations.
    """
    required = _integer(required_components, "required_components", maximum=4)
    components = compute_dip_components(
        data, lookback=lookback, min_history=min_history, quantile=quantile,
    )
    _require_boolean(components, (*COMPONENT_COLUMNS, "dip_ready_v1"))
    components["dip_component_count"] = components.loc[:, COMPONENT_COLUMNS].sum(axis=1).astype("int64")
    components["dip_condition_v1"] = (
        components["dip_ready_v1"] & components["dip_component_count"].ge(required)
    ).astype(bool)
    components["dip_event_v1"] = detect_dip_events(components)["dip_event_v1"]
    additions = components.drop(columns=["timestamp", "ticker"])
    overlap = set(data.columns) & set(additions.columns)
    if overlap:
        raise ValueError(f"Refusing to overwrite existing signal columns: {sorted(overlap)}")
    result = pd.concat([data.reset_index(drop=True), additions], axis=1)
    result.attrs = deepcopy(components.attrs)
    result.attrs["signal_parameters"].update(
        required_components=required, require_all_features=True,
        event_definition="same_ticker_condition_rising_edge",
    )
    return result
