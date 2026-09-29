"""Deterministic percentile/candidate contracts; no network or outcome research."""

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from src import signals


def measurements(values, ticker="AAPL", *, dates=None):
    """Four monotone transforms of synthetic depression values, not price bars."""
    values = np.asarray(values, dtype=float)
    return pd.DataFrame({
        "timestamp": pd.bdate_range("2024-01-01", periods=len(values))
        if dates is None else pd.DatetimeIndex(dates),
        "ticker": pd.Series([ticker] * len(values), dtype="string"),
        "drawdown_60d": values, "price_zscore_20d": values * 5,
        "distance_from_low_20d": values + 1, "relative_return_10d": values / 2,
    })


def universe(*frames):
    return pd.concat(frames, ignore_index=True).sort_values(
        ["timestamp", "ticker"]
    ).reset_index(drop=True)


def test_prior_rolling_quantiles_with_linear_interpolation_and_eviction():
    data = measurements([-.1, -.2, -.4, -.9, -.3])
    result = signals.compute_historical_thresholds(data, lookback=3, min_history=2)
    expected = np.array([np.nan, np.nan, -.18, -.32, -.70])
    np.testing.assert_allclose(result.drawdown_60d_threshold, expected, equal_nan=True)
    np.testing.assert_allclose(result.price_zscore_20d_threshold, expected * 5, equal_nan=True)
    np.testing.assert_allclose(result.distance_from_low_20d_threshold, expected + 1, equal_nan=True)
    np.testing.assert_allclose(result.relative_return_10d_threshold, expected / 2, equal_nan=True)


@pytest.mark.parametrize("feature, outlier", [
    ("drawdown_60d", -.99), ("price_zscore_20d", -1e6),
    ("distance_from_low_20d", 0), ("relative_return_10d", -1e6),
])
def test_extreme_current_value_cannot_change_its_own_threshold(feature, outlier):
    ordinary = measurements([-.1, -.2, -.3, -.15, -.25])
    original = signals.compute_historical_thresholds(ordinary, lookback=4, min_history=3)
    extreme = ordinary.copy()
    extreme.loc[3, feature] = outlier
    modified = signals.compute_historical_thresholds(extreme, lookback=4, min_history=3)
    assert_frame_equal(original.iloc[:4], modified.iloc[:4], check_exact=True)
    column = f"{feature}_threshold"
    assert modified.loc[4, column] != original.loc[4, column]  # Now it IS prior history.


@pytest.mark.parametrize("feature, flag, depressed", [
    ("drawdown_60d", "dip_drawdown_component", -.8),
    ("price_zscore_20d", "dip_price_zscore_component", -5),
    ("distance_from_low_20d", "dip_low_proximity_component", 0),
    ("relative_return_10d", "dip_relative_weakness_component", -.5),
])
def test_each_component_compares_the_correct_feature(feature, flag, depressed):
    data = measurements([-.1, -.2, -.05])
    data.loc[2, feature] = depressed
    result = signals.compute_dip_components(data, lookback=3, min_history=2)
    assert result.loc[2, flag]
    assert result.loc[2, list(signals.COMPONENT_COLUMNS)].sum() == 1
    assert result.loc[2, "dip_ready_v1"]
    for column in (*signals.COMPONENT_COLUMNS, "dip_ready_v1"):
        assert result[column].dtype == bool
        assert not result[column].isna().any()


def test_equality_ties_activate_components_without_claiming_tail_frequency():
    result = signals.compute_dip_components(measurements([-.1] * 6), lookback=3, min_history=2)
    assert not result.loc[:1, list(signals.COMPONENT_COLUMNS)].any().any()
    assert result.loc[2:, list(signals.COMPONENT_COLUMNS)].all().all()
    assert result.dip_ready_v1.tolist() == [False, False, True, True, True, True]


def test_missing_values_count_within_row_window_not_compressed_history():
    data = measurements([-.1, np.nan, -.3, -.4, np.nan, np.nan, -.7])
    result = signals.compute_dip_components(data, lookback=3, min_history=2)
    expected = [np.nan, np.nan, np.nan, -.26, -.38, -.38, np.nan]
    np.testing.assert_allclose(result.drawdown_60d_threshold, expected, equal_nan=True)
    assert result.dip_ready_v1.tolist() == [False, False, False, True, False, False, False]
    assert not result.loc[[1, 4, 5, 6], list(signals.COMPONENT_COLUMNS)].any().any()


@pytest.mark.parametrize("feature", signals.FEATURE_COLUMNS)
def test_missing_current_feature_disables_its_component_and_readiness(feature):
    data = measurements([-.1, -.2, -.8])
    data.loc[2, feature] = np.nan
    result = signals.compute_dip_components(data, lookback=3, min_history=2)
    flag = signals.COMPONENT_COLUMNS[signals.FEATURE_COLUMNS.index(feature)]
    assert not result.loc[2, flag]
    assert not result.loc[2, "dip_ready_v1"]
    assert result.loc[2, list(signals.COMPONENT_COLUMNS)].sum() == 3


def test_default_minimum_history_and_all_missing_benchmark():
    data = measurements(np.linspace(-.1, -.8, 260))
    result = signals.compute_dip_components(data)
    assert result.loc[:125, list(signals.THRESHOLD_COLUMNS)].isna().all().all()
    assert result.loc[126:, list(signals.THRESHOLD_COLUMNS)].notna().all().all()
    data["relative_return_10d"] = np.nan
    result = signals.compute_dip_components(data)
    assert result.relative_return_10d_threshold.isna().all()
    assert not result.dip_relative_weakness_component.any()
    assert not result.dip_ready_v1.any()


def test_nullable_float_missing_values_are_preserved():
    data = measurements([-.1, np.nan, -.3, -.4]).astype(
        {feature: "Float64" for feature in signals.FEATURE_COLUMNS}
    )
    result = signals.compute_dip_components(data, lookback=3, min_history=2)
    assert result.dip_ready_v1.tolist() == [False, False, False, True]
    assert result.dip_drawdown_component.dtype == bool


def test_thresholds_and_components_isolated_for_staggered_tickers():
    aapl = measurements([-.1, -.2, -.1, -.15, -.1, -.2])
    msft = measurements([-.8, -.9, -.95, -.85], "MSFT", dates=aapl.timestamp.iloc[2:])
    combined = signals.compute_dip_components(universe(aapl, msft), lookback=3, min_history=2)
    for frame in (aapl, msft):
        solo = signals.compute_dip_components(frame, lookback=3, min_history=2)
        subset = combined.loc[combined.ticker == frame.ticker.iloc[0]].reset_index(drop=True)
        assert_frame_equal(subset, solo, check_exact=True)


@pytest.mark.parametrize("kwargs", [
    {"lookback": 0}, {"lookback": -1}, {"lookback": 2.5}, {"lookback": True},
    {"lookback": "252"}, {"lookback": np.nan}, {"min_history": 0},
    {"min_history": -1}, {"min_history": 1.5}, {"min_history": False},
    {"min_history": 253}, {"quantile": -.01}, {"quantile": 1.01},
    {"quantile": np.nan}, {"quantile": np.inf}, {"quantile": True}, {"quantile": "0.2"},
])
def test_invalid_percentile_configuration(kwargs):
    with pytest.raises(ValueError):
        signals.compute_dip_components(measurements([-.1, -.2]), **kwargs)


@pytest.mark.parametrize("quantile, expected", [(0, -.3), (1, -.1)])
def test_quantile_endpoints_are_well_defined(quantile, expected):
    result = signals.compute_historical_thresholds(
        measurements([-.1, -.3, -.2]), lookback=2, min_history=2, quantile=quantile,
    )
    assert result.drawdown_60d_threshold.iloc[2] == expected


@pytest.mark.parametrize("feature", signals.FEATURE_COLUMNS)
@pytest.mark.parametrize("value", [np.inf, -np.inf])
def test_infinite_features_are_rejected(feature, value):
    data = measurements([-.1, -.2])
    data.loc[0, feature] = value
    with pytest.raises(ValueError, match="infinity"):
        signals.compute_dip_components(data)


@pytest.mark.parametrize("kind", ["string", "bool", "complex"])
def test_nonnumeric_or_boolean_features_are_rejected(kind):
    data = measurements([-.1, -.2])
    data["relative_return_10d"] = {"string": ["-1", "-2"], "bool": [True, False],
                                  "complex": [1j, 2j]}[kind]
    with pytest.raises(ValueError, match="real numeric"):
        signals.compute_dip_components(data)


def test_missing_schema_duplicate_observations_and_unsorted_input_rejected():
    valid = measurements([-.1, -.2, -.3])
    for invalid in (
        valid.drop(columns="relative_return_10d"), valid.drop(columns="timestamp"),
        pd.concat([valid, valid.iloc[-1:]]), valid.iloc[::-1], valid.iloc[:0],
        pd.concat([valid, valid[["drawdown_60d"]]], axis=1),
    ):
        with pytest.raises(ValueError):
            signals.compute_dip_components(invalid)
    with pytest.raises(TypeError):
        signals.compute_dip_components(None)


@pytest.mark.parametrize("column, value", [("ticker", " aapl"), ("ticker", None), ("timestamp", pd.NaT)])
def test_bad_identity_rejected(column, value):
    data = measurements([-.1, -.2])
    data.loc[0, column] = value
    with pytest.raises(ValueError):
        signals.compute_dip_components(data)


def test_component_api_preserves_input_and_detaches_nested_provenance():
    original = measurements([-.1, -.2, -.3])
    original.index = [9, 9, 2]
    original.attrs = {"source": {"vintage": "fixed"}}
    before = original.copy(deep=True)
    result = signals.compute_dip_components(original, lookback=2, min_history=2)
    assert_frame_equal(original, before)
    assert_frame_equal(result[["timestamp", "ticker"]], before[["timestamp", "ticker"]].reset_index(drop=True))
    result.attrs["source"]["vintage"] = "changed"
    assert original.attrs["source"]["vintage"] == "fixed"
