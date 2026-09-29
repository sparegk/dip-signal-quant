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


@pytest.mark.parametrize("active_count", range(5))
@pytest.mark.parametrize("required", [1, 2, 3, 4])
def test_component_counts_and_configurable_ready_condition(active_count, required):
    data = measurements([-.1, -.2, -.05])
    depressed = (-.8, -5, 0, -.5)
    for feature, value in zip(signals.FEATURE_COLUMNS[:active_count], depressed[:active_count]):
        data.loc[2, feature] = value
    result = signals.build_signals(data, lookback=3, min_history=2, required_components=required)
    assert result.dip_component_count.tolist() == [0, 0, active_count]
    assert result.dip_component_count.dtype == np.dtype("int64")
    expected = active_count >= required
    assert bool(result.dip_condition_v1.iloc[2]) == expected
    assert bool(result.dip_event_v1.iloc[2]) == expected
    assert result.dip_component_count.between(0, 4).all()


def test_full_builder_condition_and_event_sequence_and_reentry():
    data = measurements([-.1, -.05, -.2, -.3, -.4, -.05, -.5, -.6])
    result = signals.build_signals(data, lookback=8, min_history=2)
    assert result.dip_condition_v1.tolist() == [False, False, True, True, True, False, True, True]
    assert result.dip_event_v1.tolist() == [False, False, True, False, False, False, True, False]
    assert result.dip_component_count.tolist() == [0, 0, 4, 4, 4, 0, 4, 4]


def test_event_edges_explicitly_isolated_per_ticker():
    aapl = measurements([-.1] * 8)
    aapl["dip_condition_v1"] = [False, False, True, True, True, False, True, True]
    msft = measurements([-.1] * 8, "MSFT")
    msft["dip_condition_v1"] = [True, True, False, True, True, True, False, True]
    output = signals.detect_dip_events(universe(aapl, msft))
    assert output.loc[output.ticker == "AAPL", "dip_event_v1"].tolist() == [
        False, False, True, False, False, False, True, False,
    ]
    assert output.loc[output.ticker == "MSFT", "dip_event_v1"].tolist() == [
        True, False, False, True, False, False, False, True,
    ]


@pytest.mark.parametrize("feature", signals.FEATURE_COLUMNS)
def test_three_active_components_cannot_fire_when_fourth_value_missing(feature):
    data = measurements([-.1, -.2, -.8])
    data.loc[2, feature] = np.nan
    result = signals.build_signals(data, lookback=3, min_history=2, required_components=1)
    assert result.dip_component_count.iloc[2] == 3
    assert not result.dip_ready_v1.iloc[2]
    assert not result.dip_condition_v1.any()
    assert not result.dip_event_v1.any()


def test_missing_threshold_blocks_condition_despite_three_active_components():
    data = measurements([-.1, -.2, -.8])
    data.loc[:1, "relative_return_10d"] = np.nan
    result = signals.build_signals(data, lookback=3, min_history=2)
    assert result.dip_component_count.iloc[2] == 3
    assert not result.dip_condition_v1.any()
    assert not result.dip_event_v1.any()


def test_missing_measurement_breaks_episode_and_next_valid_dip_is_new_entry():
    data = measurements([-.1, -.2, -.3, -.4, -.5, -.6])
    data.loc[3, "relative_return_10d"] = np.nan
    result = signals.build_signals(data, lookback=6, min_history=2)
    assert result.dip_condition_v1.tolist() == [False, False, True, False, True, True]
    assert result.dip_event_v1.tolist() == [False, False, True, False, True, False]


def test_one_prior_observation_is_explicitly_configurable():
    result = signals.build_signals(measurements([-.1, -.2, -.3]), lookback=1, min_history=1)
    assert result.dip_condition_v1.tolist() == [False, True, True]
    assert result.dip_event_v1.tolist() == [False, True, False]


def test_all_nan_relative_feature_never_fires_and_absent_column_raises():
    data = measurements(np.linspace(-.1, -.8, 300))
    data["relative_return_10d"] = np.nan
    result = signals.build_signals(data)
    assert not result.dip_condition_v1.any()
    assert not result.dip_event_v1.any()
    assert result.dip_component_count.iloc[-1] == 3
    with pytest.raises(ValueError, match="relative_return_10d"):
        signals.build_signals(data.drop(columns="relative_return_10d"))


@pytest.mark.parametrize("required", [0, 5, -1, 3.0, True, "3", None, np.nan])
def test_invalid_required_components(required):
    with pytest.raises(ValueError, match="required_components"):
        signals.build_signals(measurements([-.1, -.2]), required_components=required)


@pytest.mark.parametrize("condition", [[0, 1], ["False", "True"], [False, None]])
def test_event_detection_rejects_nonboolean_or_missing_condition(condition):
    data = measurements([-.1, -.2])
    data["dip_condition_v1"] = condition
    with pytest.raises(ValueError, match="boolean"):
        signals.detect_dip_events(data)


def test_event_detection_accepts_defined_nullable_booleans_only():
    data = measurements([-.1, -.2])
    data["dip_condition_v1"] = pd.Series([False, True], dtype="boolean")
    result = signals.detect_dip_events(data)
    assert result.dip_event_v1.dtype == bool
    assert result.dip_event_v1.tolist() == [False, True]
    data.loc[0, "dip_condition_v1"] = pd.NA
    with pytest.raises(ValueError, match="boolean"):
        signals.detect_dip_events(data)


@pytest.mark.parametrize("invalid", [1, "True", pd.NA])
def test_builder_defends_against_nonboolean_component_output(monkeypatch, invalid):
    source = measurements([-.1, -.2, -.3])
    components = signals.compute_dip_components(source, lookback=2, min_history=2)
    components["dip_drawdown_component"] = invalid
    monkeypatch.setattr(signals, "compute_dip_components", lambda *args, **kwargs: components)
    with pytest.raises(ValueError, match="dip_drawdown_component.*boolean"):
        signals.build_signals(source, lookback=2, min_history=2)


def test_complete_signal_output_schema_types_no_mutation_and_provenance():
    data = measurements([-.1, -.2, -.3])
    data["note"] = "retain"
    data.index = [9, 9, 2]
    data.attrs = {"feature_benchmark": {"ticker": "SPY"}}
    before = data.copy(deep=True)
    result = signals.build_signals(data, lookback=2, min_history=2)
    expected = [*data.columns, *signals.THRESHOLD_COLUMNS, *signals.COMPONENT_COLUMNS,
                "dip_ready_v1", "dip_component_count", "dip_condition_v1", "dip_event_v1"]
    assert list(result.columns) == expected
    assert_frame_equal(result[data.columns], before.reset_index(drop=True))
    assert_frame_equal(data, before)
    assert isinstance(result.index, pd.RangeIndex)
    for column in (*signals.COMPONENT_COLUMNS, "dip_ready_v1", "dip_condition_v1", "dip_event_v1"):
        assert result[column].dtype == bool
        assert result[column].notna().all()
    assert result.attrs["signal_parameters"]["required_components"] == 3
    assert result.attrs["signal_parameters"]["require_all_features"] is True
    result.attrs["feature_benchmark"]["ticker"] = "changed"
    assert data.attrs["feature_benchmark"]["ticker"] == "SPY"
    with pytest.raises(ValueError, match="overwrite"):
        signals.build_signals(result, lookback=2, min_history=2)


def varying_measurements(length, ticker="AAPL", *, dates=None):
    i = np.arange(length)
    result = measurements(-.15 - .10 * np.sin(i / 7), ticker, dates=dates)
    result["price_zscore_20d"] = -.4 + 1.5 * np.cos(i / 11)
    result["distance_from_low_20d"] = .08 + .07 * np.sin(i / 9)
    result["relative_return_10d"] = .04 * np.cos(i / 13)
    result.loc[i % 53 == 0, list(signals.FEATURE_COLUMNS)] = [-.9, -3, 0, -.3]
    result.loc[20:27, "relative_return_10d"] = np.nan
    return result


@pytest.mark.parametrize("cutoff", [1, 125, 126, 127, 252, 253, 320])
@pytest.mark.parametrize("custom", [False, True])
def test_every_historical_signal_unchanged_by_future_append_and_extreme_changes(cutoff, custom):
    aapl = varying_measurements(400)
    msft = varying_measurements(365, "MSFT", dates=aapl.timestamp.iloc[35:])
    complete = universe(aapl, msft)
    end = aapl.timestamp.iloc[cutoff - 1]
    kwargs = {} if not custom else {
        "lookback": 12, "min_history": 6, "quantile": .3, "required_components": 2,
    }
    expected = signals.build_signals(complete.loc[complete.timestamp <= end], **kwargs)
    appended = signals.build_signals(complete, **kwargs)
    assert_frame_equal(
        appended.loc[appended.timestamp <= end].reset_index(drop=True), expected, check_exact=True,
    )
    complete.loc[complete.timestamp > end, list(signals.FEATURE_COLUMNS)] = [-.99, -1e9, 0, -1e6]
    changed = signals.build_signals(complete, **kwargs)
    assert_frame_equal(
        changed.loc[changed.timestamp <= end].reset_index(drop=True), expected, check_exact=True,
    )
    if cutoff >= 252:
        assert expected.dip_event_v1.any()  # The tested prefix includes real synthetic events.


def test_other_ticker_extreme_history_and_changes_cannot_contaminate_any_output():
    calm = varying_measurements(300)
    extreme = varying_measurements(290, "MSFT", dates=calm.timestamp.iloc[10:])
    extreme["drawdown_60d"] = np.linspace(-.8, -.95, len(extreme))
    extreme["price_zscore_20d"] = np.linspace(-3, -4, len(extreme))
    solo = signals.build_signals(calm)
    together = signals.build_signals(universe(calm, extreme))
    assert_frame_equal(together.loc[together.ticker == "AAPL"].reset_index(drop=True), solo, check_exact=True)
    extreme.loc[:, list(signals.FEATURE_COLUMNS)] = [-.99, -1e6, 0, -1e4]
    changed = signals.build_signals(universe(calm, extreme))
    assert_frame_equal(changed.loc[changed.ticker == "AAPL"].reset_index(drop=True), solo, check_exact=True)
    before_b = together.loc[together.ticker == "MSFT", list(signals.THRESHOLD_COLUMNS)]
    after_b = changed.loc[changed.ticker == "MSFT", list(signals.THRESHOLD_COLUMNS)]
    assert not before_b.equals(after_b)
    assert solo.dip_event_v1.any()


def test_event_detection_rejects_unsorted_duplicate_or_missing_condition():
    data = measurements([-.1, -.2, -.3])
    data["dip_condition_v1"] = [False, True, True]
    for invalid in (data.iloc[::-1], pd.concat([data, data.iloc[-1:]]), data.drop(columns="dip_condition_v1")):
        with pytest.raises(ValueError):
            signals.detect_dip_events(invalid)


def test_invalid_session_timestamp_representations_rejected():
    data = measurements([-.1, -.2, -.3])
    for timestamps in (data.timestamp.astype(str), data.timestamp.dt.tz_localize("UTC"),
                       data.timestamp + pd.Timedelta(hours=12), [1, 2, 3]):
        with pytest.raises(ValueError, match="timestamp"):
            signals.build_signals(data.assign(timestamp=timestamps))


def test_quantile_arithmetic_overflow_is_not_silently_a_missing_threshold():
    data = measurements([-.1, -.2, -.3])
    data["price_zscore_20d"] = [-1e308, 1e308, 0]
    with pytest.raises(ValueError, match="overflow"):
        signals.compute_historical_thresholds(data, lookback=2, min_history=2, quantile=.5)


def test_full_ohlcv_feature_signal_pipeline_warmup_and_prefix_invariance():
    from src.features import build_features

    def prices(ticker, close):
        return pd.DataFrame({
            "timestamp": pd.bdate_range("2023-01-01", periods=len(close)),
            "ticker": pd.Series([ticker] * len(close), dtype="string"),
            "open": close, "high": close + 1, "low": close - 1, "close": close,
            "volume": np.full(len(close), 100, dtype=np.int64),
        })

    i = np.arange(400)
    aapl = prices("AAPL", 100 + 10 * np.sin(i / 13))
    spy = prices("SPY", 200 + 5 * np.cos(i / 17))
    full = signals.build_signals(build_features(aapl, benchmark=spy))
    assert full.dip_ready_v1.iloc[:185].eq(False).all()
    assert full.dip_ready_v1.iloc[185:].eq(True).all()  # 59 feature warm-up + 126 prior values.
    prefix = signals.build_signals(build_features(aapl.iloc[:300], benchmark=spy.iloc[:300]))
    assert_frame_equal(full.iloc[:300], prefix, check_exact=True)
    assert prefix.dip_event_v1.any()
