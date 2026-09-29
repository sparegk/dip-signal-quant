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

## 2026-09-30 — Range, momentum, volatility, and volume measurements

- Research question: Can complementary after-close measurements preserve explicit
  initialization and undefined-value behavior without introducing signal rules?
- Hypothesis: Mean-seeded Wilder averages and full trailing sample moments provide
  testable measurements with stable historical prefixes.
- Work performed: Added RSI, True Range, ATR and ATR/close, annualized realized
  volatility, mean/relative volume, and volume z-scores. Documented smoothing,
  first-bar True Range NaN, sample standard deviations, and zero denominators.
- Result: 56 feature tests pass with warnings treated as errors. Exact small-series
  seed/recurrence calculations, constant-history limits, ticker isolation, and
  prefix tests pass. No thresholds or performance results were introduced.
- Interpretation: Numerical conventions are explicit rather than left to
  third-party indicator defaults; no new dependency was needed.
- Limitations: Wilder values depend on the historical starting point through
  their seed. Annualization assumes 252 observed sessions by default; omitted bars
  are not detected or filled by this layer.
- Next step: Add explicit benchmark alignment, market context, and final leakage
  regression coverage, then run an offline cached-data smoke check.

## 2026-09-30 — Feature engine completed with benchmark alignment

- Research question: Can market-relative measurements compare identical periods
  while retaining the feature engine's causal and multi-ticker invariants?
- Hypothesis: Exact endpoint matching and independently computed benchmark context
  avoid silently mismatching return horizons or filling unavailable market data.
- Work performed: Added optional SPY/benchmark-relative 5/10/20-bar returns and
  20-bar benchmark return, drawdown, and volatility. Added endpoint coverage tests,
  prior benchmark-history handling, configuration/provenance metadata, and complete
  V1 documentation. Recorded timing, smoothing, and alignment decisions in ADRs.
- Result: Full suite `python -m pytest -q -W error --tb=short`: 175 passed (81
  unchanged data-layer tests, 94 feature tests). Four unbenchmarked prefix cases
  and sixteen benchmark-enabled cases pass exact historical-value comparisons;
  the latter also alter future stock/benchmark OHLCV. Defaults and custom windows
  cover initialization boundaries and missing benchmark dates.
- Manual check: Loaded only existing AAPL/SPY Parquet snapshots, without network
  calls or generated output files. The builder produced 5,024 rows by 33 columns
  (7 OHLCV plus 26 measurements). NaN counts matched documented warm-ups for both
  tickers, recent rows were inspected, and no infinite feature values occurred.
- Interpretation: Feature definitions and causal calculations are validated on
  deterministic fixtures and structurally checked on cached history. No predictive
  performance, signal thresholds, or strategy results were evaluated.
- Limitations: Adjusted-data revisions and survivorship limitations persist.
  Windows count observed bars; there is no calendar-gap audit. Wilder seeds depend
  on the supplied starting history. Benchmark date matching assumes shared bar
  availability; different market close times require additional metadata.
- Next step: Specify a testable DipSignal V1 research hypothesis and candidate
  definition, including data splits and later timing assumptions, before implementing
  signal logic. DipSignal/DipScore and all strategy milestones remain unstarted.

## 2026-09-30 — Prior-history percentile dip components

- Research question: Can each ticker's own trailing feature distribution define
  transparent dip components without current-observation or cross-ticker leakage?
- Hypothesis: Concurrent lower-tail drawdown, price depression, low proximity, and
  SPY-relative weakness identify unusual observations worth later evaluation;
  no rebound or profitability claim is assumed.
- Work performed: Confirmed the 175-test baseline. Added prior-only rolling
  empirical quantiles, four boolean components, explicit complete-row readiness,
  strict input/configuration validation, and the initial signal methodology guide.
- Result: 53 deterministic signal-component tests pass with warnings treated as
  errors, including independent outlier exclusion tests for all four features.
  Thresholds use the previous 252 row positions by default and require 126 valid
  values per feature within those positions; NaNs do not compress the window.
- Interpretation: Historical comparisons are explicit and testable. Inclusive
  quantile ties can activate a component more frequently than its nominal tail.
- Limitations: Components are correlated and cannot be treated as independent
  confirmations or converted to probabilities. Missing current values or thresholds
  prevent readiness; data-vintage and calendar-completeness limitations persist.
- Next step: Add conservative condition/count logic, independent per-ticker rising
  edges, full temporal/contamination regressions, and a fixed-default frequency check.
