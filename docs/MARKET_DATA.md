# Historical market data

## Data contract

All public cleaned-data APIs return pandas frames with these columns in order:

| Column | Stored type | Meaning |
| --- | --- | --- |
| timestamp | datetime64[ns], no timezone | Exchange session date at midnight |
| ticker | string | Trimmed uppercase Yahoo symbol |
| open, high, low, close | float64 | Provider-adjusted positive OHLC |
| volume | int64 | Provider-reported nonnegative share count |

The provider call explicitly sets `interval="1d"`, `auto_adjust=True`,
`back_adjust=False`, `repair=False`, `keepna=True`, and `rounding=False`.
yfinance adjusts OHLC; this module does not apply another adjustment or adjust
volume. See the [provider download reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html).

Rows are ordered by timestamp, then ticker. Exact duplicate observations are
removed after numeric conversion; conflicting same-ticker/date rows raise.
Numeric strings are accepted, while invalid strings, booleans, complex numbers,
NaN/infinity, nonpositive prices, invalid OHLC ranges, and fractional/negative
volume raise. Zero volume is retained and does not imply liquidity.

Missing required columns or any missing required value raise, including entirely
missing provider rows. No interpolation, forward-fill, resampling, weekend/holiday
insertion, price repair, indicators, signals, or returns are performed. Missing
sessions that the provider omits entirely are not detected by a calendar audit.

Timezone removal preserves the local exchange date rather than shifting it to
UTC. Non-midnight timestamps are rejected. These dates do not represent bar
publication times or execution times. Ticker normalization preserves dots and
hyphens; use provider symbols (e.g. `BRK-B`), not arbitrary exchange aliases.

## API

Run Python from the repository root:

```python
from src.data import DEFAULT_UNIVERSE, get_history, get_histories

aapl = get_history(" aapl ")
universe = get_histories(DEFAULT_UNIVERSE)

# Dates must be supplied together; start inclusive, end exclusive.
history = get_history("AAPL", start="2015-01-01", end="2025-01-01", refresh=True)
```

Lower-level functions separate responsibilities:

- `normalize_ticker` / `normalize_tickers`: safe provider symbols; deduplication.
- `download_raw_data`: one provider request, adjusted prices and provenance.
- `clean_data`: normalize already-adjusted provider data; never re-adjust it.
- `validate_data`: assert the canonical contract without modifying a frame.
- `download_data`: download and clean without writing a snapshot.
- `save_parquet` / `load_parquet`: validated single-symbol persistence/offline reads.
- `get_history` / `get_histories`: cached single/multiple-symbol workflows.

Default download range: ten calendar years ending at today's date in
`America/New_York`, exclusive. Today's potentially incomplete US session is
excluded even after the close. Explicit end dates must also exclude today.
Leap-year subtraction uses calendar arithmetic. A newly listed stock may have
less than ten years of history; the requested interval is not a completeness claim.

## Cache and provenance

Files live at `data/market/{TICKER}.parquet`, anchored to the repository rather
than the process working directory. Pass `cache_dir=` for independent snapshots.
All generated data is ignored by Git; directory markers are tracked.

| Condition | Behavior |
| --- | --- |
| Cache absent | Download the requested range, validate, save, return |
| Cache present, default request | Validate and return the saved snapshot offline; no age check |
| Cache present, explicit dates | Select `[start, end)` offline if saved request bounds cover it |
| Requested range outside saved coverage | Raise with guidance to use `refresh=True`; no hidden download |
| `refresh=True` | Download and replace the complete symbol snapshot; never merge vintages |
| Invalid/corrupt existing cache | Raise; caller must explicitly refresh or replace it |
| Download/validation/write failure | Raise and retain the previous snapshot |

The ten-year default applies to downloads, not existing cache contents. A cache
created with a shorter range remains short until refreshed. Refreshing with a
shorter range replaces longer history; preserve experiment snapshots in a separate
directory before refreshing. Writes are atomic per file, not across a universe.
Concurrent writers are last-writer-wins; no locking or version archive is provided.

PyArrow writes Zstandard-compressed Parquet through a temporary file in the same
directory, then atomically replaces the destination. Embedded `dip_signal_quant`
metadata records schema version, ticker, interval, adjustment convention, provider
and version, requested date bounds, and UTC retrieval time for downloads. Metadata
travels with the file. Selected subsets retain original provenance and record
their narrower selection bounds. Caller-supplied frames are marked `provider=caller`
and cannot claim verified provider request coverage.

Single-symbol provenance is available as `frame.attrs["dip_signal_quant"]`;
multi-symbol results use `frame.attrs["snapshots"]`, keyed by ticker. Keep these
files, environment pins, and the code commit associated with each experiment.
Historical values may change when re-downloaded; pins alone cannot reproduce data.

## Stack and scale

- pandas receives yfinance output, normalizes schema/dates, sorts/deduplicates,
  and exposes the API expected by future VectorBT research.
- NumPy performs array-wide finiteness, positivity, and volume-domain checks.
- PyArrow handles columnar storage, compression, and embedded provenance.
- Polars is installed but deliberately unused at this scale. Future lazy Parquet
  scans can read these files directly without repeated pandas/Polars conversions.

Multiple-symbol loading deduplicates requests, reads each symbol once, and
concatenates once. Provider requests are sequential and bounded; one symbol's
calendar does not create missing rows in another. Any failed symbol raises rather
than returning an incomplete universe. Earlier successful symbol caches remain.
The combined frame is in memory; iterate `get_history` or use a future lazy scan
for larger workloads. No scaling benchmark is claimed.

## Validation and manual smoke check

```powershell
python -m pytest -q -W error
```

The suite mocks provider calls, fixes the clock, and writes temporary Parquet files.
It covers normalization, malformed input, duplicates, dates, provider contracts,
round trips, coverage checks, refreshes, multi-symbol failure, and atomic-write
failure recovery. It requires no live internet.

Optional manual check (uses the network and writes ignored local snapshots):

```powershell
python -c "from src.data import get_histories; d = get_histories(refresh=True); print(d.groupby('ticker').agg(rows=('close', 'size'), first=('timestamp', 'min'), last=('timestamp', 'max')))"
```

## Research limitations

The initial AAPL/MSFT/NVDA/AMZN/GOOGL/SPY universe is a convenience sample of
present-day survivors. It is not a historical investable universe. SPY is a planned
benchmark; no benchmark returns or strategy metrics are calculated here.

Today's adjusted history may incorporate corporate actions or corrections that
were unknown at a historical signal time. It is not a point-in-time database;
absolute price levels and volume/notional interpretations need particular care.
Future features must respect information availability and execution timing.

The US session cutoff does not establish global-market completeness. There is no
exchange-calendar audit, symbol-change/security-master mapping, delisting guarantee,
corporate-action event archive, automatic retry policy, or alternative provider.
Provider outages and rate limits are surfaced. Structural tests do not establish
economic accuracy, absence of bias, or profitability.
