"""Deterministic data contract tests; all provider access is mocked."""

from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src import data


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(data.yf, "download", Mock(side_effect=AssertionError("Unexpected network call")))


@pytest.fixture
def raw():
    return pd.DataFrame(
        {"Open": [100.0, 102.0], "High": [104.0, 105.0], "Low": [99.0, 101.0],
         "Close": [103.0, 104.0], "Volume": [1000, 2000]},
        index=pd.DatetimeIndex(["2024-01-05", "2024-01-08"], name="Date"),
    )


@pytest.mark.parametrize("value, expected", [(" aapl ", "AAPL"), ("brk-b", "BRK-B"), ("7203.t", "7203.T"), ("^gspc", "^GSPC")])
def test_ticker_normalization(value, expected):
    assert data.normalize_ticker(value) == expected


@pytest.mark.parametrize("value", ["", " ", "../AAPL", "A APL", "AAPL/MSFT", "CON", "nul.txt", "LPT1", "AAPL."])
def test_unsafe_symbols_rejected(value):
    with pytest.raises(ValueError):
        data.normalize_ticker(value)


def test_ticker_collections():
    assert data.normalize_tickers("aapl") == ("AAPL",)
    assert data.normalize_tickers([" aapl", "MSFT", "AAPL"]) == ("AAPL", "MSFT")
    with pytest.raises(ValueError):
        data.normalize_tickers([])
    with pytest.raises(TypeError):
        data.normalize_ticker(None)


def test_schema_sorting_coercion_and_no_artificial_dates(raw):
    raw["Volume"] = raw["Volume"].astype(str)
    original = raw.copy(deep=True)
    cleaned = data.clean_data(raw.iloc[::-1], " aapl ")
    assert tuple(cleaned.columns) == data.COLUMNS
    assert cleaned["timestamp"].tolist() == list(original.index)
    assert cleaned["ticker"].tolist() == ["AAPL", "AAPL"]
    assert str(cleaned["volume"].dtype) == "int64"
    assert str(cleaned["close"].dtype) == "float64"
    assert len(cleaned) == 2  # Friday and Monday; no weekend observations.
    assert_frame_equal(raw, original)


@pytest.mark.parametrize("column", ["Open", "High", "Low", "Close", "Volume"])
def test_required_columns(raw, column):
    with pytest.raises(ValueError, match="Missing required columns"):
        data.clean_data(raw.drop(columns=column), "AAPL")


def test_exact_duplicates_removed_conflicts_rejected(raw):
    expected = data.clean_data(raw, "AAPL")
    assert_frame_equal(data.clean_data(pd.concat([raw, raw.iloc[:1]]), "AAPL"), expected)
    conflicting = raw.iloc[:1].copy()
    conflicting["Close"] = 102.0
    with pytest.raises(ValueError, match="Duplicate ticker/timestamp"):
        data.clean_data(pd.concat([raw, conflicting]), "AAPL")


@pytest.mark.parametrize("column, value, message", [
    ("Close", np.nan, "Missing required"), ("Volume", np.nan, "Missing required"),
    ("Close", np.inf, "finite"), ("Open", 0, "positive"), ("Low", -1, "positive"),
    ("Close", 150, "Malformed OHLC"), ("High", 98, "Malformed OHLC"),
    ("Volume", -1, "nonnegative"), ("Volume", 1.5, "nonnegative"),
    ("Volume", 2**63, "nonnegative"), ("Close", "oops", "numeric"),
    ("Close", True, "numeric"), ("Volume", False, "numeric"),
    ("Close", 1 + 2j, "numeric"),
])
def test_malformed_values_rejected(raw, column, value, message):
    raw[column] = raw[column].astype(object)
    raw.loc[raw.index[0], column] = value
    with pytest.raises(ValueError, match=message):
        data.clean_data(raw, "AAPL")


def test_empty_and_all_missing_rows_rejected(raw):
    with pytest.raises(ValueError, match="empty"):
        data.clean_data(raw.iloc[:0], "AAPL")
    raw.loc[raw.index[0], :] = np.nan
    with pytest.raises(ValueError, match="Missing required"):
        data.clean_data(raw, "AAPL")


def test_timezone_preserves_local_session_dates(raw):
    raw.index = raw.index.tz_localize("Asia/Tokyo")
    cleaned = data.clean_data(raw, "AAPL")
    assert cleaned["timestamp"].dt.strftime("%Y-%m-%d").tolist() == ["2024-01-05", "2024-01-08"]
    assert cleaned["timestamp"].dt.tz is None


@pytest.mark.parametrize("dates", [["bad", "2024-01-08"], [None, "2024-01-08"], [1, 2], ["2024-01-05 12:00", "2024-01-08 12:00"]])
def test_invalid_timestamps_rejected(raw, dates):
    raw = raw.reset_index(drop=True)
    raw["timestamp"] = dates
    with pytest.raises(ValueError):
        data.clean_data(raw, "AAPL")


@pytest.mark.parametrize("ticker_first", [False, True])
def test_single_ticker_multiindex_columns(raw, ticker_first):
    expected = data.clean_data(raw, "AAPL")
    raw.columns = pd.MultiIndex.from_tuples([(c, "AAPL") for c in raw.columns])
    if ticker_first:
        raw.columns = raw.columns.swaplevel()
    assert_frame_equal(data.clean_data(raw, "AAPL"), expected)
    with pytest.raises(ValueError, match="only MSFT"):
        data.clean_data(raw, "MSFT")


def test_duplicate_column_labels_rejected(raw):
    raw["close"] = raw["Close"]
    with pytest.raises(ValueError, match="Duplicate column"):
        data.clean_data(raw, "AAPL")


def test_validate_does_not_silently_clean(raw):
    clean = data.clean_data(raw, "AAPL")
    with pytest.raises(ValueError, match="sorted"):
        data.validate_data(clean.iloc[::-1])
    with pytest.raises(ValueError, match="Duplicate ticker/timestamp"):
        data.validate_data(pd.concat([clean, clean]))
    with pytest.raises(ValueError, match="Missing required columns"):
        data.validate_data(clean.drop(columns="ticker"))


def test_download_contract_and_provenance(raw, monkeypatch):
    mock = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", mock)
    clean = data.download_data("aapl", start="2024-01-01", end="2024-02-01")
    args, kwargs = mock.call_args
    assert args == ("AAPL",)
    assert kwargs["auto_adjust"] is True
    assert kwargs["interval"] == "1d"
    assert kwargs["keepna"] is True
    assert kwargs["repair"] is False
    assert kwargs["start"] == "2024-01-01"
    assert kwargs["end"] == "2024-02-01"
    assert clean["close"].tolist() == raw["Close"].tolist()  # No second adjustment.
    assert clean.attrs[data.PROVENANCE_KEY]["ticker"] == "AAPL"
    assert "retrieved_at" in clean.attrs[data.PROVENANCE_KEY]


def test_default_lookback_excludes_today(raw, monkeypatch):
    class FixedDatetime:
        @staticmethod
        def now(tz):
            return pd.Timestamp("2024-02-29 12:00", tz=tz).to_pydatetime()

    monkeypatch.setattr(data, "datetime", FixedDatetime)
    mock = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", mock)
    data.download_data("AAPL")
    assert mock.call_args.kwargs["start"] == "2014-02-28"
    assert mock.call_args.kwargs["end"] == "2024-02-29"


@pytest.mark.parametrize("start, end", [("2024-01-01", None), (None, "2024-01-01"), ("2024-02-01", "2024-01-01"), ("2024-01-01", "2024-01-01"), ("2024-02-30", "2024-03-01"), ("2024-1-1", "2024-02-01"), ("2024-01-01", "9999-01-01")])
def test_invalid_date_requests_fail_before_network(start, end):
    with pytest.raises(ValueError):
        data.download_raw_data("AAPL", start=start, end=end)
    data.yf.download.assert_not_called()


@pytest.mark.parametrize("response", [None, pd.DataFrame()])
def test_empty_download_fails(response, monkeypatch):
    monkeypatch.setattr(data.yf, "download", Mock(return_value=response))
    with pytest.raises(RuntimeError, match="AAPL"):
        data.download_raw_data("AAPL")


def test_provider_exception_has_ticker_context(monkeypatch):
    monkeypatch.setattr(data.yf, "download", Mock(side_effect=TimeoutError("timed out")))
    with pytest.raises(RuntimeError, match="AAPL.*timed out"):
        data.download_raw_data("AAPL")


def test_out_of_range_provider_bars_rejected(raw, monkeypatch):
    monkeypatch.setattr(data.yf, "download", Mock(return_value=raw))
    with pytest.raises(ValueError, match="outside the requested range"):
        data.download_data("AAPL", start="2024-01-08", end="2024-02-01")
