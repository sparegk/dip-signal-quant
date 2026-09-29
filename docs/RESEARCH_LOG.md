# Research log

Append dated entries in chronological order. Record inconclusive and failed work
as well as successful results; link experiment IDs and decisions when relevant.

## Entry template

- Date:
- Research question:
- Hypothesis:
- Work performed:
- Result:
- Interpretation:
- Limitations:
- Next step:

## 2026-09-30 — Project foundation

- Research question: Can statistically unusual short-term equity dips identify
  repeatable mean-reversion opportunities after realistic trading costs?
- Hypothesis: To be specified and tested; no trading edge is assumed.
- Work performed: Inspected the repository and established persistent project
  instructions, a roadmap, decision records, and an experiment registry.
- Result: Research documentation established. First implementation objective:
  reliable historical daily OHLCV ingestion.
- Interpretation: Data quality and reproducibility must precede signal research.
- Limitations: No strategy, performance result, or validated signal exists.
  The initial six-symbol convenience universe is not survivorship-bias-free.
- Next step: Implement and deterministically test adjusted historical ingestion,
  validation, and Parquet caching.

## 2026-09-30 — Historical ingestion contract

- Research question: Can daily provider history be normalized without silently
  repairing missing or contradictory observations?
- Hypothesis: Explicit validation and deterministic fixtures can establish a
  reliable structural contract before using live data for research.
- Work performed: Added single-symbol yfinance ingestion, a ten-calendar-year
  default, explicit date ranges, adjusted OHLC, symbol normalization, numeric and
  timestamp validation, and tests with mocked provider responses.
- Result: 58 deterministic tests pass. Exact duplicates are removed; conflicting
  duplicates and missing required values raise. No trading metrics were measured.
- Interpretation: The ingestion contract is tested; this does not establish
  provider accuracy or strategy performance.
- Limitations: US session-date cutoff; today's session excluded. No calendar-gap
  audit, delisting history guarantee, or point-in-time adjustment data.
- Next step: Implement persistent Parquet caching and multi-symbol loading.
