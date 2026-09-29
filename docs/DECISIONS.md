# Decisions

Lightweight architecture decision records. Append new entries when decisions
change; preserve their context rather than rewriting the research history.

## ADR-001 — Daily timeframe for V1

Date: 2026-09-30. Status: Accepted.

Decision: Begin with daily equity data before considering intraday signals.

Reason: Simpler research environment, longer clean history, faster iteration,
and lower noise. Daily observations still require careful signal availability
and execution timing; a completed bar cannot inform an earlier fill.

## ADR-002 — Parquet as persistent market-data format

Date: 2026-09-30. Status: Accepted.

Decision: Store cleaned history in one Parquet file per normalized ticker under
`data/market/`; exclude generated data from Git.

Reason: Columnar storage, compression, and compatibility with pandas, Polars,
PyArrow, and future DuckDB queries. Symbol files allow independent refreshes.

## ADR-003 — Research-first architecture

Date: 2026-09-30. Status: Accepted.

Decision: Validate signal quality before building UI, broker integrations, or
live execution.

Reason: Reproducible evidence should drive system complexity. Infrastructure
alone is not evidence of predictive power or profitability.

## ADR-004 — Hybrid pandas / Polars / NumPy stack

Date: 2026-09-30. Status: Accepted.

Decision: Use the right tool for each workload rather than forcing all processing
through one dataframe library.

Reason: pandas naturally receives yfinance data and supports future VectorBT
research. NumPy provides array validation and numerical operations. Polars is
reserved for workloads such as lazy Parquet scans when they offer a real benefit.
Avoid repeated conversions; use PyArrow for Parquet persistence and metadata.

## ADR-005 — Explicit adjustment and validation contract

Date: 2026-09-30. Status: Accepted.

Decision: Request daily yfinance auto-adjusted OHLC and retain provider-reported
volume. Reject missing or malformed bars, remove only identical duplicates, and
exclude today's potentially incomplete US session. Preserve exchange session dates.

Reason: Avoid implicit library defaults, hidden filling, and accidental inclusion
of partial daily bars. Current adjusted history is not point-in-time data; later
research must account for corporate-action revisions and signal availability.

## ADR-006 — Explicit, atomic per-symbol cache snapshots

Date: 2026-09-30. Status: Accepted.

Decision: Existing snapshots load offline until explicitly refreshed. Save request
provenance in Parquet metadata and replace an entire symbol history atomically.
Explicit date requests outside known coverage raise instead of returning a silently
truncated history. Download symbols sequentially and concatenate cleaned data once.

Reason: Preserve failed-refresh recovery and keep adjustment vintages consistent.
Snapshots are convenient local caches, not immutable experiment archives; users
must preserve experiment inputs before refreshing. Sequential requests bound traffic
and avoid cross-symbol date padding; optimize concurrency only with evidence.

## ADR-007 — After-close, per-ticker feature availability

Date: 2026-09-30. Status: Accepted.

Decision: Calculate features independently by ticker using full trailing windows
of observed bars. Features at t include t's completed bar and are available after
the close; later execution generally occurs at t+1 or later. Preserve all warm-up
NaNs. Reuse data validation without changing the market-data API.

Reason: Explicit timing and ticker boundaries prevent accidental future-data use
or cross-symbol windows. Adding/changing future observations must leave historical
features unchanged. Observed-bar causality does not remove data-vintage bias or
guarantee complete exchange calendars.

## ADR-008 — Explicit indicator initialization and undefined values

Date: 2026-09-30. Status: Accepted.

Decision: Use arithmetic-mean-seeded Wilder smoothing for RSI/ATR. True Range is
undefined without a previous close; n-period RSI/ATR first appear on bar n+1.
Use sample standard deviations (ddof=1) and annualize return volatility by sqrt(252)
by default. Zero-denominator z-scores, all-flat RSI, and all-zero relative-volume
windows remain NaN. These are measurements without signal thresholds.

Reason: Indicator conventions must be reproducible and testable rather than
implicit dependency defaults. pandas/NumPy suffice without a new TA dependency.
Wilder averages retain a decaying dependency on the initial history/seed.

## ADR-009 — Benchmark returns use matched timestamp endpoints

Date: 2026-09-30. Status: Accepted.

Decision: Require an explicit single-ticker benchmark, normally SPY. Relative
returns compare the stock and benchmark over the stock's exact n-bar endpoints;
either missing benchmark endpoint yields NaN. Compute market context on the
benchmark's own history, then join on exact session date without filling.

Reason: Independently shifting stock/benchmark rows can compare different periods
when calendars differ. Context must retain benchmark history before stock inception.
The date-based convention assumes both instruments' bars are available at the
calculation time; cross-market publication timing needs additional metadata.

## ADR template

- ID and title:
- Date / status:
- Decision:
- Reason:
- Consequences and limitations:
- Supersedes (if applicable):
