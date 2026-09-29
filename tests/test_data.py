"""Deterministic data contract tests; all provider access is mocked."""

from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest
from pandas.testing import assert_frame_equal
import pyarrow as pa
import pyarrow.parquet as pq

from src import data


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    monkeypatch.setattr(data.yf, "download", Mock(side_effect=AssertionError("Unexpected network call")))


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    class FixedDatetime:
        @staticmethod
        def now(tz):
            return pd.Timestamp("2026-09-30 12:00", tz=tz).to_pydatetime()

    monkeypatch.setattr(data, "datetime", FixedDatetime)


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
    ("Close", 1 + 2j, "numeric"), ("Close", np.complex64(1 + 2j), "numeric"),
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


def test_parquet_round_trip_with_provenance(raw, monkeypatch, tmp_path):
    monkeypatch.setattr(data.yf, "download", Mock(return_value=raw))
    clean = data.download_data("AAPL", start="2024-01-01", end="2024-02-01")
    path = data.save_parquet(clean, tmp_path / "nested" / "AAPL.parquet")
    loaded = data.load_parquet(path, ticker="aapl")
    assert_frame_equal(loaded, clean)
    assert loaded.attrs == clean.attrs
    assert data.PROVENANCE_KEY.encode() in pq.read_schema(path).metadata


def test_caller_supplied_snapshot_and_missing_file(raw, tmp_path):
    clean = data.clean_data(raw, "AAPL")
    path = data.save_parquet(clean, tmp_path / "AAPL.parquet")
    loaded = data.load_parquet(path)
    assert_frame_equal(loaded, clean)
    assert loaded.attrs[data.PROVENANCE_KEY]["provider"] == "caller"
    with pytest.raises(FileNotFoundError):
        data.load_parquet(tmp_path / "missing.parquet")


def test_cache_miss_then_offline_hit(raw, monkeypatch, tmp_path):
    provider = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", provider)
    fresh = data.get_history(" aapl ", cache_dir=tmp_path, start="2024-01-01", end="2024-02-01")
    assert (tmp_path / "AAPL.parquet").exists()
    provider.assert_called_once()
    provider.side_effect = AssertionError("Cache hit must be offline")
    cached = data.get_history("AAPL", cache_dir=tmp_path)
    assert_frame_equal(cached, fresh)
    assert cached.attrs == fresh.attrs
    provider.assert_called_once()


def test_refresh_replaces_entire_snapshot(raw, monkeypatch, tmp_path):
    provider = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", provider)
    data.get_history("AAPL", cache_dir=tmp_path, start="2024-01-01", end="2024-02-01")
    revised = raw.iloc[1:].copy()
    revised["Close"] = 103.5
    provider.return_value = revised
    fresh = data.get_history("AAPL", cache_dir=tmp_path, refresh=True, start="2024-01-08", end="2024-02-01")
    assert provider.call_count == 2
    assert len(fresh) == 1
    assert fresh["close"].tolist() == [103.5]
    assert_frame_equal(data.load_parquet(tmp_path / "AAPL.parquet"), fresh)


def test_failed_download_and_invalid_refresh_preserve_cache(raw, monkeypatch, tmp_path):
    provider = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", provider)
    data.get_history("AAPL", cache_dir=tmp_path)
    path = tmp_path / "AAPL.parquet"
    original = path.read_bytes()
    provider.side_effect = TimeoutError("unavailable")
    with pytest.raises(RuntimeError):
        data.get_history("AAPL", cache_dir=tmp_path, refresh=True)
    assert path.read_bytes() == original
    provider.side_effect = None
    malformed = raw.copy()
    malformed["Close"] = np.nan
    provider.return_value = malformed
    with pytest.raises(ValueError):
        data.get_history("AAPL", cache_dir=tmp_path, refresh=True)
    assert path.read_bytes() == original


def test_failed_parquet_write_preserves_cache_and_removes_temp(raw, monkeypatch, tmp_path):
    clean = data.clean_data(raw, "AAPL")
    path = data.save_parquet(clean, tmp_path / "AAPL.parquet")
    original = path.read_bytes()
    monkeypatch.setattr(data.pq, "write_table", Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        data.save_parquet(clean, path)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_failed_atomic_replace_preserves_cache(raw, monkeypatch, tmp_path):
    clean = data.clean_data(raw, "AAPL")
    path = data.save_parquet(clean, tmp_path / "AAPL.parquet")
    original = path.read_bytes()
    monkeypatch.setattr(data.os, "replace", Mock(side_effect=PermissionError("locked")))
    with pytest.raises(PermissionError, match="locked"):
        data.save_parquet(clean, path)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_explicit_cache_subset_and_coverage(raw, monkeypatch, tmp_path):
    provider = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", provider)
    data.get_history("AAPL", cache_dir=tmp_path, start="2024-01-01", end="2024-02-01")
    subset = data.get_history("AAPL", cache_dir=tmp_path, start="2024-01-05", end="2024-01-08")
    assert subset["timestamp"].tolist() == [pd.Timestamp("2024-01-05")]
    with pytest.raises(ValueError, match="refresh=True"):
        data.get_history("AAPL", cache_dir=tmp_path, start="2023-01-01", end="2024-02-01")
    with pytest.raises(ValueError, match="No cached observations"):
        data.get_history("AAPL", cache_dir=tmp_path, start="2024-01-06", end="2024-01-08")
    with pytest.raises(ValueError, match="both start and end"):
        data.get_history("AAPL", cache_dir=tmp_path, start="2024-01-01")
    provider.assert_called_once()


def test_unknown_request_coverage_requires_explicit_refresh(raw, tmp_path):
    data.save_parquet(data.clean_data(raw, "AAPL"), tmp_path / "AAPL.parquet")
    with pytest.raises(ValueError, match="refresh=True"):
        data.get_history("AAPL", cache_dir=tmp_path, start="2024-01-01", end="2024-02-01")
    data.yf.download.assert_not_called()


def test_saved_subset_does_not_claim_original_request_coverage(raw, monkeypatch, tmp_path):
    monkeypatch.setattr(data.yf, "download", Mock(return_value=raw))
    data.get_history("AAPL", cache_dir=tmp_path, start="2024-01-01", end="2024-02-01")
    subset = data.get_history("AAPL", cache_dir=tmp_path, start="2024-01-05", end="2024-01-08")
    data.save_parquet(subset, tmp_path / "subset" / "AAPL.parquet")
    with pytest.raises(ValueError, match="refresh=True"):
        data.get_history("AAPL", cache_dir=tmp_path / "subset", start="2024-01-01", end="2024-02-01")
    assert subset.attrs[data.PROVENANCE_KEY]["requested_end"] == "2024-02-01"
    assert subset.attrs[data.PROVENANCE_KEY]["selection_end"] == "2024-01-08"


def test_wrong_ticker_cache_fails_offline(raw, tmp_path):
    data.save_parquet(data.clean_data(raw, "MSFT"), tmp_path / "AAPL.parquet")
    with pytest.raises(ValueError, match="requested AAPL"):
        data.get_history("AAPL", cache_dir=tmp_path)
    data.yf.download.assert_not_called()


def test_multiple_tickers_fetch_only_missing_and_deduplicate(raw, monkeypatch, tmp_path):
    provider = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", provider)
    data.get_history("AAPL", cache_dir=tmp_path)
    combined = data.get_histories([" msft", "aapl", "MSFT"], cache_dir=tmp_path)
    assert [call.args[0] for call in provider.call_args_list] == ["AAPL", "MSFT"]
    assert combined["ticker"].tolist() == ["AAPL", "MSFT", "AAPL", "MSFT"]
    assert len(combined) == 4
    assert set(combined.attrs["snapshots"]) == {"AAPL", "MSFT"}
    data.validate_data(combined)
    assert_frame_equal(data.get_histories(["AAPL", "MSFT"], cache_dir=tmp_path), combined)
    assert provider.call_count == 2


def test_initial_universe_and_refresh_all(raw, monkeypatch, tmp_path):
    provider = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", provider)
    combined = data.get_histories(cache_dir=tmp_path)
    assert set(combined["ticker"]) == set(data.DEFAULT_UNIVERSE)
    assert provider.call_count == 6
    data.get_histories(cache_dir=tmp_path, refresh=True)
    assert provider.call_count == 12
    assert len(list(tmp_path.glob("*.parquet"))) == 6


def test_multisymbol_failure_is_not_silently_omitted(raw, monkeypatch, tmp_path):
    provider = Mock(side_effect=[raw, pd.DataFrame()])
    monkeypatch.setattr(data.yf, "download", provider)
    with pytest.raises(RuntimeError, match="MSFT"):
        data.get_histories(["AAPL", "MSFT"], cache_dir=tmp_path)
    assert (tmp_path / "AAPL.parquet").exists()
    assert not (tmp_path / "MSFT.parquet").exists()


def test_single_string_and_empty_multisymbol_requests(raw, monkeypatch, tmp_path):
    provider = Mock(return_value=raw)
    monkeypatch.setattr(data.yf, "download", provider)
    assert set(data.get_histories("aapl", cache_dir=tmp_path)["ticker"]) == {"AAPL"}
    with pytest.raises(ValueError, match="At least one"):
        data.get_histories([], cache_dir=tmp_path)
    provider.assert_called_once()


def test_storage_rejects_malformed_and_multisymbol_frames(raw, tmp_path):
    clean = data.clean_data(raw, "AAPL")
    invalid = clean.copy()
    invalid.loc[0, "close"] = np.nan
    with pytest.raises(ValueError):
        data.save_parquet(invalid, tmp_path / "invalid.parquet")
    multiple = pd.concat([clean, data.clean_data(raw, "MSFT")]).sort_values(["timestamp", "ticker"])
    with pytest.raises(ValueError, match="exactly one ticker"):
        data.save_parquet(multiple, tmp_path / "multiple.parquet")
    assert list(tmp_path.iterdir()) == []


def test_parquet_without_provenance_rejected(raw, tmp_path):
    path = tmp_path / "AAPL.parquet"
    data.clean_data(raw, "AAPL").to_parquet(path, index=False)
    with pytest.raises(ValueError, match="provenance"):
        data.get_history("AAPL", cache_dir=tmp_path)
    data.yf.download.assert_not_called()


def test_invalid_bars_in_existing_parquet_rejected(raw, tmp_path):
    path = data.save_parquet(data.clean_data(raw, "AAPL"), tmp_path / "AAPL.parquet")
    table = pq.read_table(path)
    invalid = table.to_pandas()
    invalid.loc[0, "close"] = -1.0
    tampered = pa.Table.from_pandas(invalid, preserve_index=False).replace_schema_metadata(table.schema.metadata)
    pq.write_table(tampered, path)
    with pytest.raises(ValueError, match="positive"):
        data.load_parquet(path)


@pytest.mark.parametrize("metadata, message", [(b"not-json", "Invalid snapshot"), (b"[]", "Unsupported"), (b'{"schema_version": 999}', "Unsupported"), (b'{"schema_version": 1, "interval": "1h"}', "daily")])
def test_invalid_snapshot_metadata_rejected(raw, tmp_path, metadata, message):
    path = data.save_parquet(data.clean_data(raw, "AAPL"), tmp_path / "AAPL.parquet")
    table = pq.read_table(path)
    updated = dict(table.schema.metadata)
    updated[data.PROVENANCE_KEY.encode()] = metadata
    pq.write_table(table.replace_schema_metadata(updated), path)
    with pytest.raises(ValueError, match=message):
        data.load_parquet(path)
