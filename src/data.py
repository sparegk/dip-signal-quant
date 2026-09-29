"""Daily adjusted equity OHLCV ingestion; no features or trading logic.

Prices use yfinance ``auto_adjust=True`` (split/dividend-adjusted OHLC).
Volume is the provider's reported volume, not dividend-adjusted by this module.
Timestamps are timezone-naive exchange session dates, not UTC instants or times
at which a bar was available. Current adjusted history is not point-in-time data.
"""

from collections.abc import Iterable
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yfinance as yf


DEFAULT_UNIVERSE = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "SPY")
COLUMNS = ("timestamp", "ticker", "open", "high", "low", "close", "volume")
PRICE_COLUMNS = ("open", "high", "low", "close")
NUMERIC_COLUMNS = (*PRICE_COLUMNS, "volume")
PROVENANCE_KEY = "dip_signal_quant"
DEFAULT_CACHE_DIR = Path(__file__).resolve().parents[1] / "data" / "market"


def normalize_ticker(ticker: str) -> str:
    """Trim and uppercase a Yahoo symbol, preserving dots and hyphens.

    Reject unsafe filenames and Windows device names. Exchange suffixes are not
    translated; callers must use the provider's symbol (for example, BRK-B).
    """
    if not isinstance(ticker, str):
        raise TypeError("ticker must be a string")
    symbol = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z0-9^][A-Z0-9.^=-]{0,31}", symbol):
        raise ValueError(f"Invalid ticker: {ticker!r}")
    base = symbol.split(".")[0]
    if symbol.endswith(".") or base in ("CON", "PRN", "AUX", "NUL") or re.fullmatch(
        r"(?:COM|LPT)[1-9]", base
    ):
        raise ValueError(f"Ticker cannot be used as a cache filename: {symbol!r}")
    return symbol


def normalize_tickers(tickers: str | Iterable[str]) -> tuple[str, ...]:
    """Normalize and deduplicate symbols, preserving first occurrence order."""
    values = (tickers,) if isinstance(tickers, str) else tickers
    symbols = tuple(dict.fromkeys(normalize_ticker(value) for value in values))
    if not symbols:
        raise ValueError("At least one ticker is required")
    return symbols


def _date_range(start: str | None, end: str | None) -> tuple[str, str]:
    """Resolve [start, end); exclude today's potentially incomplete US session."""
    today = datetime.now(ZoneInfo("America/New_York")).date()
    if start is None and end is None:
        end = today.isoformat()
        start = (pd.Timestamp(today) - pd.DateOffset(years=10)).date().isoformat()
    elif start is None or end is None:
        raise ValueError("Provide both start and end, or neither")
    for value in (start, end):
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("start and end must be ISO dates (YYYY-MM-DD)")
        date.fromisoformat(value)
    if start >= end:
        raise ValueError("start must precede exclusive end")
    if date.fromisoformat(end) > today:
        raise ValueError("end must not include today's incomplete US session")
    return start, end


def download_raw_data(
    ticker: str, *, start: str | None = None, end: str | None = None
) -> pd.DataFrame:
    """Download one daily adjusted history; default to ten calendar years.

    Explicit dates must be supplied together: start inclusive, end exclusive.
    Keep missing provider rows so cleaning can reject them explicitly. Disable
    automatic repair and rounding; do not conceal questionable observations.
    """
    symbol = normalize_ticker(ticker)
    start, end = _date_range(start, end)
    try:
        raw = yf.download(
            symbol, start=start, end=end, interval="1d", auto_adjust=True,
            back_adjust=False, actions=False, repair=False, keepna=True,
            rounding=False, progress=False, threads=False, ignore_tz=True,
            multi_level_index=False, timeout=30,
        )
    except Exception as exc:
        raise RuntimeError(f"Download failed for {symbol}: {exc}") from exc
    if not isinstance(raw, pd.DataFrame) or raw.empty:
        raise RuntimeError(f"No historical data returned for {symbol}")
    raw = raw.copy()
    raw.attrs[PROVENANCE_KEY] = {
        "schema_version": 1,
        "provider": "yfinance",
        "provider_version": yf.__version__,
        "ticker": symbol,
        "interval": "1d",
        "adjustment": "auto_adjust=True; provider-reported volume",
        "requested_start": start,
        "requested_end": end,
        "retrieved_at": datetime.now(ZoneInfo("UTC")).isoformat(),
    }
    return raw


def _require_columns(data: pd.DataFrame, required: tuple[str, ...]) -> None:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame")
    if not data.columns.is_unique:
        raise ValueError("Duplicate column labels are not allowed")
    missing = set(required) - set(data.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    if data.empty:
        raise ValueError("Market data must not be empty")


def validate_data(data: pd.DataFrame) -> None:
    """Reject noncanonical, missing, nonfinite, duplicate, or malformed bars.

    Require positive OHLC within each bar's low/high, nonnegative integer volume,
    and ascending (timestamp, ticker) order. Zero volume is retained, not treated
    as proof of liquidity. This validates structure, not calendar completeness.
    """
    _require_columns(data, COLUMNS)
    if data.loc[:, COLUMNS].isna().any().any():
        raise ValueError("Missing required data; prices and volume are never filled")
    timestamps = data["timestamp"]
    if not pd.api.types.is_datetime64_dtype(timestamps.dtype):
        raise ValueError("timestamp must be timezone-naive datetime64")
    if not timestamps.eq(timestamps.dt.normalize()).all():
        raise ValueError("timestamp must represent a daily session date at midnight")
    if not all(isinstance(t, str) and normalize_ticker(t) == t for t in data["ticker"].unique()):
        raise ValueError("ticker values must be normalized strings")
    for column in NUMERIC_COLUMNS:
        dtype = data[column].dtype
        if (not pd.api.types.is_numeric_dtype(dtype)
                or pd.api.types.is_bool_dtype(dtype)
                or pd.api.types.is_complex_dtype(dtype)):
            raise ValueError(f"{column} must contain real numeric values")
    numbers = data.loc[:, NUMERIC_COLUMNS].to_numpy(dtype=np.float64)
    if not np.isfinite(numbers).all():
        raise ValueError("OHLCV must contain finite values")
    prices = numbers[:, :4]
    if (prices <= 0).any():
        raise ValueError("OHLC prices must be positive")
    if ((data["low"] > data["high"])
            | (data["open"] < data["low"]) | (data["open"] > data["high"])
            | (data["close"] < data["low"]) | (data["close"] > data["high"])).any():
        raise ValueError("Malformed OHLC: open/close must lie within low/high")
    volume = numbers[:, 4]
    if ((volume < 0) | (volume >= 2**63) | (volume != np.floor(volume))).any():
        raise ValueError("volume must be a nonnegative int64 count")
    if not pd.api.types.is_integer_dtype(data["volume"].dtype):
        raise ValueError("volume must use an integer dtype")
    if data.duplicated(["ticker", "timestamp"]).any():
        raise ValueError("Duplicate ticker/timestamp observations")
    keys = pd.MultiIndex.from_frame(data[["timestamp", "ticker"]])
    if not keys.is_monotonic_increasing:
        raise ValueError("Data must be sorted by timestamp, then ticker")


def clean_data(raw: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Normalize already-adjusted provider data into the seven-column schema.

    Do not adjust prices a second time. Missing/invalid required values raise;
    identical rows are deduplicated, conflicting same-session bars raise. Local
    timezone information is removed without shifting the exchange session date.
    """
    symbol = normalize_ticker(ticker)
    if not isinstance(raw, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame")
    frame = raw.copy()
    if isinstance(frame.columns, pd.MultiIndex):
        if frame.columns.nlevels != 2:
            raise ValueError("Expected two provider column levels")
        for level in (0, 1):
            labels = frame.columns.get_level_values(level)
            if all(isinstance(label, str) and label.strip().upper() == symbol for label in labels):
                frame.columns = frame.columns.droplevel(level)
                break
        else:
            raise ValueError(f"Provider columns do not describe only {symbol}")
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    _require_columns(frame, NUMERIC_COLUMNS)
    if "ticker" in frame and not frame["ticker"].map(normalize_ticker).eq(symbol).all():
        raise ValueError(f"Input contains a ticker other than {symbol}")
    if "timestamp" in frame:
        dates = frame["timestamp"]
    elif "date" in frame:
        dates = frame["date"]
    elif isinstance(frame.index, pd.DatetimeIndex):
        dates = frame.index
    else:
        raise ValueError("Expected a DatetimeIndex or timestamp/date column")
    if pd.api.types.is_numeric_dtype(dates.dtype):
        raise ValueError("Numeric timestamps are ambiguous; supply session dates")
    try:
        timestamps = pd.DatetimeIndex(pd.to_datetime(dates, errors="raise", format="ISO8601"))
        if timestamps.tz is not None:
            timestamps = timestamps.tz_localize(None)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid session timestamps") from exc
    cleaned = frame.loc[:, NUMERIC_COLUMNS].reset_index(drop=True).copy()
    cleaned.insert(0, "ticker", pd.Series([symbol] * len(cleaned), dtype="string"))
    cleaned.insert(0, "timestamp", timestamps.astype("datetime64[ns]"))
    for column in NUMERIC_COLUMNS:
        if cleaned[column].map(
            lambda value: isinstance(value, (bool, np.bool_, complex, np.complexfloating))
        ).any():
            raise ValueError(f"{column} must contain real numeric values, not booleans")
        try:
            cleaned[column] = pd.to_numeric(cleaned[column], errors="raise")
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric values in {column}") from exc
    if cleaned.isna().any().any():
        raise ValueError("Missing required data; prices and volume are never filled")
    numbers = cleaned.loc[:, NUMERIC_COLUMNS].to_numpy(dtype=np.float64)
    if not np.isfinite(numbers).all():
        raise ValueError("OHLCV must contain finite values")
    volume = numbers[:, 4]
    if ((volume < 0) | (volume >= 2**63) | (volume != np.floor(volume))).any():
        raise ValueError("volume must be a nonnegative int64 count")
    cleaned = cleaned.astype({**{c: "float64" for c in PRICE_COLUMNS}, "volume": "int64"})
    cleaned = cleaned.drop_duplicates().sort_values(["timestamp", "ticker"]).reset_index(drop=True)
    validate_data(cleaned)
    cleaned.attrs = raw.attrs.copy()
    return cleaned


def download_data(
    ticker: str, *, start: str | None = None, end: str | None = None
) -> pd.DataFrame:
    """Download and validate one adjusted history without persistent caching."""
    raw = download_raw_data(ticker, start=start, end=end)
    cleaned = clean_data(raw, ticker)
    request = cleaned.attrs[PROVENANCE_KEY]
    if not ((cleaned["timestamp"] >= request["requested_start"])
            & (cleaned["timestamp"] < request["requested_end"])).all():
        raise ValueError(f"Provider returned observations outside the requested range for {ticker}")
    return cleaned


def save_parquet(data: pd.DataFrame, path: str | Path) -> Path:
    """Atomically save a validated, single-symbol snapshot using PyArrow.

    Store provenance in the same file as the bars. Caller-supplied frames must
    already contain adjusted OHLC; their adjustment history cannot be inferred.
    A failed validation/write leaves any existing snapshot intact. Concurrent
    successful writers use last-writer-wins semantics; no locking is provided.
    """
    validate_data(data)
    symbols = data["ticker"].unique()
    if len(symbols) != 1:
        raise ValueError("A Parquet snapshot must contain exactly one ticker")
    provenance = dict(data.attrs.get(PROVENANCE_KEY, {}))
    if provenance.get("ticker", symbols[0]) != symbols[0]:
        raise ValueError("Provenance ticker does not match the data")
    provenance.update(schema_version=1, ticker=symbols[0], interval="1d")
    provenance.setdefault("provider", "caller")
    provenance.setdefault("adjustment", "caller-supplied adjusted OHLC; provider-reported volume")
    table = pa.Table.from_pandas(data.loc[:, COLUMNS], preserve_index=False)
    metadata = dict(table.schema.metadata or {})
    metadata[PROVENANCE_KEY.encode()] = json.dumps(provenance, sort_keys=True).encode()
    table = table.replace_schema_metadata(metadata)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        pq.write_table(table, temporary_path, compression="zstd")
        os.replace(temporary_path, destination)
    finally:
        temporary_path.unlink(missing_ok=True)
    return destination


def load_parquet(path: str | Path, *, ticker: str | None = None) -> pd.DataFrame:
    """Read and validate a snapshot written by save_parquet, entirely offline.

    Reject corrupt/unrecognized snapshots; never silently download replacements.
    Pass ticker to ensure a cache filename has not been associated with wrong data.
    """
    expected = normalize_ticker(ticker) if ticker is not None else None
    table = pq.read_table(Path(path))
    encoded = (table.schema.metadata or {}).get(PROVENANCE_KEY.encode())
    if encoded is None:
        raise ValueError("Missing snapshot provenance; refresh or recreate this cache")
    try:
        provenance = json.loads(encoded)
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid snapshot provenance") from exc
    if not isinstance(provenance, dict) or provenance.get("schema_version") != 1:
        raise ValueError("Unsupported market-data snapshot schema")
    if provenance.get("interval") != "1d":
        raise ValueError("Snapshot must contain daily data")
    frame = table.to_pandas()
    validate_data(frame)
    symbols = frame["ticker"].unique()
    if len(symbols) != 1 or symbols[0] != provenance.get("ticker"):
        raise ValueError("Snapshot ticker does not match its provenance")
    if expected is not None and symbols[0] != expected:
        raise ValueError(f"Snapshot ticker does not match requested {expected}")
    frame.attrs = {PROVENANCE_KEY: provenance}
    return frame.loc[:, COLUMNS].reset_index(drop=True)


def get_history(
    ticker: str,
    *,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    refresh: bool = False,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Load cached history or download, validate, and persist on a cache miss.

    Existing cache + refresh=False: return the saved snapshot without any network
    call or age check. Explicit dates select a subset only when saved request
    bounds cover them; otherwise raise and require refresh=True. Coverage refers
    to the provider request, not a guarantee of every trading session.

    Cache miss or refresh=True: fetch the requested range (default ten years)
    and replace this symbol's complete snapshot atomically. Refresh does not merge
    differently adjusted vintages and may shorten history if given a shorter range.
    """
    symbol = normalize_ticker(ticker)
    explicit_dates = start is not None or end is not None
    if explicit_dates:
        start, end = _date_range(start, end)
    path = Path(cache_dir) / f"{symbol}.parquet"
    if path.exists() and not refresh:
        cached = load_parquet(path, ticker=symbol)
        if explicit_dates:
            provenance = cached.attrs[PROVENANCE_KEY]
            saved_start = provenance.get("selection_start", provenance.get("requested_start"))
            saved_end = provenance.get("selection_end", provenance.get("requested_end"))
            if (not isinstance(saved_start, str) or not isinstance(saved_end, str)
                    or saved_start > start or saved_end < end):
                raise ValueError(f"Cache for {symbol} does not cover request; use refresh=True")
            cached = cached.loc[
                (cached["timestamp"] >= start) & (cached["timestamp"] < end)
            ].reset_index(drop=True)
            if cached.empty:
                raise ValueError(f"No cached observations for {symbol} in requested range")
            cached.attrs = {PROVENANCE_KEY: {
                **provenance, "selection_start": start, "selection_end": end,
            }}
        return cached
    fresh = download_data(symbol, start=start, end=end)
    save_parquet(fresh, path)
    return fresh


def get_histories(
    tickers: str | Iterable[str] = DEFAULT_UNIVERSE,
    *,
    cache_dir: str | Path = DEFAULT_CACHE_DIR,
    refresh: bool = False,
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Return normalized symbols in one long-form, time-sorted pandas frame.

    Read/download each unique symbol once and concatenate once. Sequential
    provider requests keep traffic bounded and avoid cross-symbol NaN padding.
    Any failed symbol raises; earlier successful per-symbol cache writes remain.
    Each symbol's provenance is available in attrs['snapshots']. For larger-than-
    memory workflows, iterate get_history or scan the Parquet files directly.
    """
    symbols = normalize_tickers(tickers)
    frames = [get_history(symbol, cache_dir=cache_dir, refresh=refresh, start=start, end=end)
              for symbol in symbols]
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values(["timestamp", "ticker"]).reset_index(drop=True)
    combined.attrs = {"snapshots": {
        symbol: frame.attrs[PROVENANCE_KEY] for symbol, frame in zip(symbols, frames)
    }}
    validate_data(combined)
    return combined
