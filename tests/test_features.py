"""Small numerical fixtures and temporal invariants; never use live data."""

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from src import features


def bars(closes, ticker="AAPL", *, dates=None, volume=None):
    """Construct valid synthetic daily OHLCV, with zero intraday range."""
    close = np.asarray(closes, dtype=float)
    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=len(close), freq="B")
        if dates is None else pd.DatetimeIndex(dates),
        "ticker": pd.Series([ticker] * len(close), dtype="string"),
        "open": close, "high": close, "low": close, "close": close,
        "volume": np.full(len(close), 100, dtype=np.int64)
        if volume is None else np.asarray(volume, dtype=np.int64),
    })


def universe(*frames):
    return pd.concat(frames, ignore_index=True).sort_values(
        ["timestamp", "ticker"]
    ).reset_index(drop=True)


def test_exact_trailing_returns():
    output = features.compute_returns(bars([10, 12, 9, 18]), windows=(1, 2))
    np.testing.assert_allclose(output.return_1d, [np.nan, .2, -.25, 1], equal_nan=True)
    np.testing.assert_allclose(output.return_2d, [np.nan, np.nan, -.1, .5], equal_nan=True)


def test_locations_use_close_extrema_and_full_trailing_window():
    data = bars([10, 12, 9, 11, 8])
    data["high"] += 100  # Features measure close extrema, not intraday extrema.
    output = features.compute_price_location_features(data, windows=(3,))
    np.testing.assert_allclose(
        output.drawdown_3d, [np.nan, np.nan, 9 / 12 - 1, 11 / 12 - 1, 8 / 11 - 1],
        equal_nan=True,
    )
    np.testing.assert_allclose(
        output.distance_from_low_3d, [np.nan, np.nan, 0, 11 / 9 - 1, 0], equal_nan=True,
    )
    np.testing.assert_array_equal(output.drawdown_3d, output.distance_from_high_3d)


def test_zscore_sample_std_and_flat_window():
    output = features.compute_price_zscores(bars([1, 2, 3, 3, 3]), windows=(3,))
    np.testing.assert_allclose(
        output.price_zscore_3d, [np.nan, np.nan, 1, 1 / np.sqrt(3), np.nan], equal_nan=True,
    )


def test_builder_identity_input_and_metadata_are_preserved():
    original = bars([10, 12, 11, 13])
    original.index = [9, 9, 3, 2]  # Row labels are not the observation identity.
    original.attrs = {"source": {"snapshot": "fixed"}}
    original["note"] = "retained"
    before = original.copy(deep=True)
    output = features.build_features(original)
    assert_frame_equal(output[original.columns], before.reset_index(drop=True))
    assert_frame_equal(original, before)
    output.attrs["source"]["snapshot"] = "changed"
    assert original.attrs["source"]["snapshot"] == "fixed"


def test_multiple_ticker_isolation_and_unequal_histories():
    aapl = bars([10, 12, 8, 11, 14, 9])
    msft = bars([1000, 500, 800, 200], "MSFT", dates=aapl.timestamp.iloc[2:])
    combined = features.build_features(universe(aapl, msft), location_windows=(2, 3), zscore_windows=(2,))
    for frame in (aapl, msft):
        solo = features.build_features(frame, location_windows=(2, 3), zscore_windows=(2,))
        actual = combined.loc[combined.ticker == frame.ticker.iloc[0]].reset_index(drop=True)
        assert_frame_equal(actual, solo)


@pytest.mark.parametrize("cutoff", [1, 5, 25, 65])
def test_future_append_does_not_change_price_features(cutoff):
    aapl = bars(100 + np.sin(np.arange(90)) * 5 + np.arange(90) * .1)
    msft = bars(200 + np.cos(np.arange(90)) * 20, "MSFT")
    complete = universe(aapl, msft)
    end = aapl.timestamp.iloc[cutoff - 1]
    past = complete.loc[complete.timestamp <= end]
    expected = features.build_features(past)
    actual = features.build_features(complete).loc[lambda d: d.timestamp <= end]
    assert_frame_equal(actual.reset_index(drop=True), expected, check_exact=True)


@pytest.mark.parametrize("window", [0, -1, True, 2.5, "3", np.nan])
def test_invalid_windows(window):
    with pytest.raises(ValueError, match="Windows"):
        features.compute_returns(bars([1, 2, 3]), windows=(window,))


def test_window_normalization_and_empty_windows():
    output = features.compute_returns(bars([1, 2, 3]), windows=(2, 1, 2))
    assert list(output.columns) == ["timestamp", "ticker", "return_1d", "return_2d"]
    with pytest.raises(ValueError):
        features.compute_returns(bars([1, 2, 3]), windows=())
    with pytest.raises(ValueError):
        features.compute_price_zscores(bars([1, 2, 3]), windows=(1,))


@pytest.mark.parametrize("column, value", [
    ("close", np.nan), ("close", np.inf), ("close", 0), ("close", -1),
    ("volume", -1), ("ticker", " aapl"), ("timestamp", pd.NaT),
])
def test_malformed_values_are_not_hidden(column, value):
    data = bars([10, 11, 12])
    data.loc[0, column] = value
    with pytest.raises(ValueError):
        features.build_features(data)


def test_missing_columns_duplicates_unsorted_and_empty_are_rejected():
    data = bars([10, 11, 12])
    for malformed in (
        data.drop(columns="close"), pd.concat([data, data.iloc[-1:]]),
        data.iloc[::-1], data.iloc[:0],
    ):
        with pytest.raises(ValueError):
            features.build_features(malformed)


def test_feature_collision_is_rejected():
    data = bars([10, 11, 12])
    data["return_1d"] = 999.0
    with pytest.raises(ValueError, match="overwrite"):
        features.build_features(data)


def test_extreme_numeric_overflow_is_rejected():
    with pytest.raises(ValueError, match="overflow"):
        features.compute_returns(bars([1e-300, 1e300]), windows=(1,))


def test_default_price_feature_warmups_and_invariants():
    output = features.build_features(bars(100 + np.sin(np.arange(80))))
    for n in (1, 5, 10, 20):
        assert output[f"return_{n}d"].iloc[:n].isna().all()
        assert output[f"return_{n}d"].iloc[n:].notna().all()
    for n in (20, 60):
        assert output[f"drawdown_{n}d"].iloc[:n - 1].isna().all()
        assert output[f"drawdown_{n}d"].dropna().le(0).all()
        assert output[f"distance_from_low_{n}d"].dropna().ge(0).all()
    assert output.price_zscore_20d.iloc[:19].isna().all()


def test_rsi_exact_seed_and_wilder_recurrence():
    # First changes +2,-1,+3: avg gain=5/3, loss=1/3 => RSI=100*5/6.
    # Next -2: gain=10/9, loss=8/9 => RSI=100*5/9.
    # Next +1: gain=29/27, loss=16/27 => RSI=100*29/45.
    output = features.compute_rsi(bars([10, 12, 11, 14, 12, 13]), window=3)
    np.testing.assert_allclose(
        output.rsi_3, [np.nan] * 3 + [100 * 5 / 6, 100 * 5 / 9, 100 * 29 / 45],
        equal_nan=True,
    )


@pytest.mark.parametrize("closes, expected", [
    ([1, 2, 3, 4, 5], 100), ([5, 4, 3, 2, 1], 0), ([3, 3, 3, 3, 3], np.nan),
])
def test_rsi_monotone_and_constant_limits(closes, expected):
    result = features.compute_rsi(bars(closes), window=3).rsi_3
    assert result.iloc[:3].isna().all()
    np.testing.assert_allclose(result.iloc[3:], expected, equal_nan=True)


def test_rsi_starts_after_flat_history_without_future_filling():
    output = features.compute_rsi(bars([10, 10, 10, 10, 11, 10]), window=3)
    assert output.rsi_3.iloc[:4].isna().all()
    np.testing.assert_allclose(output.rsi_3.iloc[4:], [100, 40])


def test_true_range_gaps_and_atr_exact_seed_and_recurrence():
    data = bars([10, 13, 10, 10, 12])
    data["high"] = [11, 14, 11, 12, 13]
    data["low"] = [9, 12, 9, 9, 11]
    output = features.compute_atr(data, window=3)
    # High vs prior close wins on bar 2; low vs prior close on bar 3;
    # intraday range wins on bar 4. First bar has no previous close.
    np.testing.assert_allclose(output.true_range, [np.nan, 4, 4, 3, 3], equal_nan=True)
    expected = [np.nan] * 3 + [11 / 3, 31 / 9]
    np.testing.assert_allclose(output.atr_3, expected, equal_nan=True)
    np.testing.assert_allclose(output.atr_pct_3, np.array(expected) / data.close, equal_nan=True)


def test_atr_one_period_equals_defined_true_range():
    output = features.compute_atr(bars([10, 12, 11, 15]), window=1)
    np.testing.assert_array_equal(output.atr_1, output.true_range)


def test_volatility_exact_daily_sample_std_and_annualization():
    data = bars([100, 110, 99, 108.9])  # +10%, -10%, +10%.
    daily = features.compute_volatility(data, windows=(2,), annualization=1)
    annual = features.compute_volatility(data, windows=(2,))
    expected = np.sqrt(.02)
    np.testing.assert_allclose(daily.volatility_2d, [np.nan, np.nan, expected, expected], equal_nan=True)
    np.testing.assert_allclose(annual.volatility_2d, daily.volatility_2d * np.sqrt(252), equal_nan=True)


def test_volume_mean_relative_and_zscore():
    output = features.compute_volume_features(bars([10] * 4, volume=[100, 200, 300, 0]), windows=(3,))
    np.testing.assert_allclose(output.volume_mean_3d, [np.nan, np.nan, 200, 500 / 3], equal_nan=True)
    np.testing.assert_allclose(output.relative_volume_3d, [np.nan, np.nan, 1.5, 0], equal_nan=True)
    expected_last = (0 - 500 / 3) / np.std([200, 300, 0], ddof=1)
    np.testing.assert_allclose(output.volume_zscore_3d, [np.nan, np.nan, 1, expected_last], equal_nan=True)


@pytest.mark.parametrize("volume", [0, 100])
def test_constant_price_and_volume_undefined_denominators(volume):
    output = features.build_features(bars([10] * 75, volume=[volume] * 75))
    assert output.price_zscore_20d.isna().all()
    assert output.rsi_14.isna().all()
    assert output.volume_zscore_20d.isna().all()
    assert output.volatility_20d.iloc[20:].eq(0).all()
    assert output.atr_14.iloc[14:].eq(0).all()
    assert output.atr_pct_14.iloc[14:].eq(0).all()
    assert output.volume_mean_20d.iloc[19:].eq(volume).all()
    if volume == 0:
        assert output.relative_volume_20d.isna().all()
    else:
        assert output.relative_volume_20d.iloc[19:].eq(1).all()
    assert not np.isinf(output.select_dtypes("number").to_numpy()).any()


def test_default_indicator_warmups_and_ranges():
    output = features.build_features(bars(100 + 10 * np.sin(np.arange(80))))
    for column, warmup in {
        "true_range": 1, "rsi_14": 14, "atr_14": 14, "atr_pct_14": 14,
        "volatility_20d": 20, "volatility_60d": 60,
        "volume_mean_20d": 19, "relative_volume_20d": 19,
    }.items():
        assert output[column].iloc[:warmup].isna().all(), column
        assert output[column].iloc[warmup:].notna().all(), column
    assert output.rsi_14.dropna().between(0, 100).all()
    for column in ("true_range", "atr_14", "atr_pct_14", "volatility_20d", "volatility_60d"):
        assert output[column].dropna().ge(0).all(), column


@pytest.mark.parametrize("function, kwargs", [
    (features.compute_rsi, {"window": 1}), (features.compute_atr, {"window": 0}),
    (features.compute_volume_features, {"windows": (1,)}),
    (features.compute_volatility, {"windows": (1,)}),
    (features.compute_volatility, {"annualization": 0}),
    (features.compute_volatility, {"annualization": -1}),
    (features.compute_volatility, {"annualization": np.inf}),
    (features.compute_volatility, {"annualization": True}),
    (features.compute_volatility, {"annualization": "252"}),
])
def test_invalid_indicator_configuration(function, kwargs):
    with pytest.raises(ValueError):
        function(bars([10, 11, 12]), **kwargs)


@pytest.mark.parametrize("function", [
    features.compute_returns, features.compute_price_location_features,
    features.compute_price_zscores, features.compute_rsi, features.compute_atr,
    features.compute_volatility, features.compute_volume_features,
])
def test_modular_apis_match_builder_for_multiple_tickers(function):
    data = universe(
        bars(100 + 5 * np.sin(np.arange(80))),
        bars(200 + 15 * np.cos(np.arange(80)), "MSFT", volume=np.arange(80) * 10),
    )
    module = function(data)
    complete = features.build_features(data)
    assert_frame_equal(module, complete[module.columns])


def test_all_indicators_isolated_after_warmup_on_staggered_histories():
    aapl = bars(100 + np.sin(np.arange(90)), volume=np.arange(90) * 10)
    msft = bars(300 + 50 * np.cos(np.arange(70)), "MSFT", dates=aapl.timestamp.iloc[20:])
    combined = features.build_features(universe(aapl, msft))
    for original in (aapl, msft):
        actual = combined.loc[combined.ticker == original.ticker.iloc[0]].reset_index(drop=True)
        assert_frame_equal(actual, features.build_features(original), check_exact=True)


def test_relative_returns_exact_and_benchmark_context():
    stock = bars([10, 12, 9, 18, 15])
    benchmark = bars([100, 105, 110, 100, 125], "SPY")
    output = features.compute_relative_features(stock, benchmark, windows=(1, 2), context_window=2)
    np.testing.assert_allclose(
        output.relative_return_2d,
        [np.nan, np.nan, 9 / 10 - 110 / 100, 18 / 12 - 100 / 105, 15 / 9 - 125 / 110],
        equal_nan=True,
    )
    np.testing.assert_allclose(
        output.benchmark_return_2d, [np.nan, np.nan, .1, 100 / 105 - 1, 125 / 110 - 1],
        equal_nan=True,
    )
    np.testing.assert_allclose(
        output.benchmark_drawdown_2d, [np.nan, 0, 0, 100 / 110 - 1, 0], equal_nan=True,
    )
    first_vol = np.std([105 / 100 - 1, 110 / 105 - 1], ddof=1) * np.sqrt(252)
    assert output.benchmark_volatility_2d.iloc[2] == pytest.approx(first_vol)


def test_missing_benchmark_dates_require_both_endpoints_without_fill():
    stock = bars([10, 12, 9, 18, 15])
    benchmark = bars([100, 110, 100, 125], "SPY", dates=stock.timestamp.iloc[[0, 2, 3, 4]])
    output = features.compute_relative_features(stock, benchmark, windows=(2,), context_window=2)
    assert output.loc[1].drop(labels=["timestamp", "ticker"]).isna().all()
    assert output.relative_return_2d.iloc[2] == pytest.approx(9 / 10 - 110 / 100)
    assert pd.isna(output.relative_return_2d.iloc[3])  # Start endpoint missing.
    assert output.relative_return_2d.iloc[4] == pytest.approx(15 / 9 - 125 / 110)
    assert pd.isna(output.benchmark_return_2d.iloc[2])  # Only 2 benchmark bars.
    assert output.benchmark_return_2d.iloc[3] == pytest.approx(100 / 100 - 1)
    assert len(output) == len(stock)


def test_missing_stock_dates_do_not_change_relative_return_endpoint():
    benchmark = bars([100, 200, 300, 400, 500], "SPY")
    stock = bars([10, 15, 20, 25], dates=benchmark.timestamp.iloc[[0, 2, 3, 4]])
    output = features.compute_relative_features(stock, benchmark, windows=(2,), context_window=2)
    # Stock's 2-bar lag at timestamp[3] is timestamp[0], not benchmark's timestamp[1].
    assert output.relative_return_2d.iloc[2] == pytest.approx(20 / 10 - 400 / 100)
    assert output.benchmark_return_2d.iloc[2] == pytest.approx(400 / 200 - 1)


def test_benchmark_context_keeps_history_before_stock_inception():
    benchmark = bars(100 + np.arange(30), "SPY")
    stock = bars([10, 11], dates=benchmark.timestamp.iloc[-2:])
    output = features.compute_relative_features(stock, benchmark)
    assert output.benchmark_return_20d.notna().all()
    assert output.benchmark_volatility_20d.notna().all()
    assert output.relative_return_5d.isna().all()


def test_benchmark_is_explicit_and_self_relative_returns_are_zero():
    benchmark = bars(100 + np.sin(np.arange(70)), "SPY")
    plain = features.build_features(benchmark)
    assert not any(c.startswith(("relative_return_", "benchmark_")) for c in plain)
    measured = features.build_features(benchmark, benchmark=benchmark)
    for n in (5, 10, 20):
        assert measured[f"relative_return_{n}d"].iloc[:n].isna().all()
        assert measured[f"relative_return_{n}d"].iloc[n:].eq(0).all()
    assert measured.benchmark_return_20d.iloc[:20].isna().all()
    assert measured.benchmark_drawdown_20d.iloc[:19].isna().all()
    assert measured.benchmark_volatility_20d.iloc[:20].isna().all()


def test_no_overlap_benchmark_leaves_rows_and_nan_features():
    stock = bars([10, 11, 12])
    benchmark = bars([100, 101, 102], "SPY", dates=pd.bdate_range("2025-01-01", periods=3))
    output = features.compute_relative_features(stock, benchmark, windows=(1,), context_window=2)
    assert_frame_equal(output[["timestamp", "ticker"]], stock[["timestamp", "ticker"]])
    assert output.iloc[:, 2:].isna().all().all()


@pytest.mark.parametrize("kind", ["multiple", "duplicate", "missing", "nan", "empty", "unsorted"])
def test_bad_benchmark_input_rejected(kind):
    benchmark = bars([100, 101, 102], "SPY")
    if kind == "multiple":
        benchmark = universe(benchmark, bars([50, 51, 52], "QQQ"))
    elif kind == "duplicate":
        benchmark = pd.concat([benchmark, benchmark.iloc[-1:]])
    elif kind == "missing":
        benchmark = benchmark.drop(columns="close")
    elif kind == "nan":
        benchmark.loc[0, "close"] = np.nan
    elif kind == "empty":
        benchmark = benchmark.iloc[:0]
    else:
        benchmark = benchmark.iloc[::-1]
    with pytest.raises(ValueError):
        features.build_features(bars([10, 11, 12]), benchmark=benchmark)


def test_relative_modular_api_isolation_metadata_and_custom_parameters():
    benchmark = bars(100 + np.arange(70), "SPY")
    benchmark.attrs = {"snapshot": {"version": "original"}}
    aapl = bars(20 + np.sin(np.arange(70)))
    msft = bars(50 + np.cos(np.arange(65)), "MSFT", dates=aapl.timestamp.iloc[5:])
    combined = universe(aapl, msft)
    original = combined.copy(deep=True)
    benchmark_original = benchmark.copy(deep=True)
    output = features.build_features(
        combined, benchmark=benchmark, relative_windows=(2, 4), context_window=3, annualization=1,
    )
    modular = features.compute_relative_features(
        combined, benchmark, windows=(2, 4), context_window=3, annualization=1,
    )
    assert_frame_equal(output[modular.columns], modular)
    for stock in (aapl, msft):
        solo = features.build_features(
            stock, benchmark=benchmark, relative_windows=(2, 4), context_window=3, annualization=1,
        )
        subset = output.loc[output.ticker == stock.ticker.iloc[0]].reset_index(drop=True)
        assert_frame_equal(subset, solo, check_exact=True)
    output.attrs["feature_benchmark"]["provenance"]["snapshot"]["version"] = "modified"
    assert benchmark.attrs["snapshot"]["version"] == "original"
    assert_frame_equal(benchmark, benchmark_original)
    assert_frame_equal(combined, original)
    assert output.attrs["feature_parameters"]["relative_windows"] == (2, 4)


@pytest.mark.parametrize("cutoff", [1, 13, 14, 19, 20, 59, 60, 70])
@pytest.mark.parametrize("custom", [False, True])
def test_all_features_unchanged_by_appending_or_altering_future_stock_and_benchmark(cutoff, custom):
    benchmark = bars(200 + np.sin(np.arange(110)) * 10, "SPY")
    dates = benchmark.timestamp.iloc[10:100]
    aapl = bars(100 + np.sin(np.arange(90)) * 5, dates=dates, volume=np.arange(90) * 100)
    msft = bars(300 + np.cos(np.arange(85)) * 20, "MSFT", dates=dates.iloc[5:])
    complete = universe(aapl, msft)
    # A missing benchmark date remains absent, not filled by future information.
    benchmark = benchmark.drop(index=[12, 45, 81]).reset_index(drop=True)
    end = aapl.timestamp.iloc[cutoff - 1]
    past = complete.loc[complete.timestamp <= end]
    past_benchmark = benchmark.loc[benchmark.timestamp <= end]
    kwargs = {} if not custom else {
        "return_windows": (2, 3), "location_windows": (3, 7), "zscore_windows": (3, 7),
        "rsi_window": 3, "atr_window": 4, "volume_windows": (3,),
        "volatility_windows": (3, 7), "relative_windows": (2, 3), "context_window": 3,
    }
    expected = features.build_features(past, benchmark=past_benchmark, **kwargs)
    appended = features.build_features(complete, benchmark=benchmark, **kwargs)
    assert_frame_equal(
        appended.loc[appended.timestamp <= end].reset_index(drop=True), expected, check_exact=True,
    )
    for frame, factor in ((complete, 20), (benchmark, .01)):
        frame.loc[frame.timestamp > end, ["open", "high", "low", "close"]] *= factor
        frame.loc[frame.timestamp > end, "volume"] *= 3
    altered = features.build_features(complete, benchmark=benchmark, **kwargs)
    assert_frame_equal(
        altered.loc[altered.timestamp <= end].reset_index(drop=True), expected, check_exact=True,
    )


@pytest.mark.parametrize("function", [
    features.compute_returns, features.compute_price_location_features,
    features.compute_price_zscores, features.compute_rsi, features.compute_atr,
    features.compute_volatility, features.compute_volume_features,
])
def test_each_public_family_rejects_malformed_data(function):
    data = bars([10, 11, 12])
    data.loc[0, "volume"] = -1
    with pytest.raises(ValueError):
        function(data)


def test_schema_types_and_duplicate_columns_are_rejected():
    valid = bars([10, 11, 12])
    malformed = [valid.astype({"close": str}), valid.assign(volume=1.5),
                 valid.assign(volume=True), pd.concat([valid, valid[["close"]]], axis=1),
                 valid.assign(timestamp=valid.timestamp.dt.tz_localize("UTC"))]
    for frame in malformed:
        with pytest.raises(ValueError):
            features.build_features(frame)
    with pytest.raises(TypeError):
        features.build_features(None)


def test_complete_default_column_contract():
    benchmark = bars(100 + np.sin(np.arange(75)), "SPY")
    result = features.build_features(benchmark, benchmark=benchmark)
    expected = [*benchmark.columns, "return_1d", "return_5d", "return_10d", "return_20d",
                "drawdown_20d", "distance_from_low_20d", "distance_from_high_20d",
                "drawdown_60d", "distance_from_low_60d", "distance_from_high_60d",
                "price_zscore_20d", "rsi_14", "true_range", "atr_14", "atr_pct_14",
                "volatility_20d", "volatility_60d", "volume_mean_20d",
                "relative_volume_20d", "volume_zscore_20d", "relative_return_5d",
                "relative_return_10d", "relative_return_20d", "benchmark_return_20d",
                "benchmark_drawdown_20d", "benchmark_volatility_20d"]
    assert list(result.columns) == expected
