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

## ADR template

- ID and title:
- Date / status:
- Decision:
- Reason:
- Consequences and limitations:
- Supersedes (if applicable):
