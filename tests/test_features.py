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
