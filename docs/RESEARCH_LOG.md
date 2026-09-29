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

## 2026-09-30 — Historical market-data layer completed

- Research question: Can validated multi-symbol history be reused offline with
  explicit provenance and safe refresh behavior?
- Hypothesis: Independent, atomic Parquet snapshots can support reproducible local
  research without automatically changing historical inputs between runs.
- Work performed: Added per-symbol Parquet storage with embedded provenance,
  offline cache reads, explicit refresh, request/subset coverage checks, and
  multi-symbol loading. Documented the API, adjustment convention, and limitations.
  Added a fixed test clock and mocked network, storage, and refresh failure tests.
- Result: `python -m pytest -q -W error --tb=short`: 81 passed. `python -m pip check`:
  no broken requirements. A separate live smoke download returned 2,512 rows each
  for AAPL, MSFT, NVDA, AMZN, GOOGL, and SPY (15,072 total), spanning 2016-09-29
  through 2026-09-28. All 15,072 rows subsequently loaded from cache with the
  provider call patched to raise on any network attempt. Generated market files
  remain local and ignored by Git.
- Interpretation: Structural validation, persistence, failure recovery, and the
  live provider integration are working. No signal quality or investment
  performance has been measured.
- Limitations: Provider corrections and current adjustments are not point-in-time
  data. No calendar-completeness audit or survivorship-free universe. Explicit
  refresh replaces the previous snapshot; preserve experiment datasets separately.
  Existing environment pins target Windows/Python 3.14 rather than a portable lock.
- Issues encountered: Windows sandbox restrictions initially blocked pytest's
  temporary directory and the live Yahoo connection; reruns with the required
  access succeeded. A saved-subset coverage issue was caught in review and fixed
  with a regression test before completion.
- Next step: Define and implement a small, leakage-aware feature engine with
  explicit feature availability and deterministic rolling-window tests. This
  milestone has not been started.

## 2026-09-30 — Core trailing price features

- Research question: Can price measurements be computed per ticker without using
  observations beyond their session date?
- Hypothesis: Trailing shifts/windows with explicit warm-ups should be invariant
  to appending future observations to a fixed historical data vintage.
- Work performed: Established an 81-test clean baseline; added returns, rolling
  close drawdowns, high/low distances, and sample-standard-deviation price z-scores.
  Added shared validation, ticker isolation, and a configurable feature builder.
- Result: 27 deterministic feature tests pass with warnings treated as errors,
  including exact prefix invariance at four cutoffs. No strategy was evaluated.
- Interpretation: Core price measurements satisfy the tested causal contract.
- Limitations: Observed-bar windows are not exchange-calendar completeness checks;
  provider adjustments remain subject to the documented data-vintage limitation.
- Next step: Add Wilder RSI/ATR, realized volatility, and volume measurements.
