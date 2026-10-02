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

## 2026-09-30 — DipSignal V1 candidate engine completed

- Research question: Can concurrent self-relative lower-tail measurements identify
  transparent dip candidates without self-inclusion, future-data, or ticker leakage?
- Hypothesis: At least three of four depressed dimensions may identify observations
  worth later outcome evaluation; no rebound or profitable strategy is assumed.
- Work performed: Added integer component counts, complete-row eligibility, V1
  conditions, and independent per-ticker rising-edge events. Kept fixed defaults
  (252 prior positions, 126 valid observations, 0.20 quantile, three components).
  Documented linear interpolation, inclusive ties, missing-data event semantics,
  after-close availability, and architectural decisions in ADR-010/011.
- Result: `python -m pytest -q -W error --tb=short`: 293 passed (175 unchanged
  data/feature tests plus 118 signal tests), with warnings treated as errors.
  Fourteen default/custom-window regressions compare all historical outputs exactly
  after both appending and drastically modifying future rows. Four feature-specific
  current-outlier exclusion tests pass. Adding/altering an extreme second ticker
  leaves the calm ticker unchanged. End-to-end OHLCV/feature/signal prefix and
  warm-up checks also pass.
- Sanity check: Loaded existing AAPL and SPY caches only, with provider downloading
  patched to fail if attempted. AAPL as the target and SPY as benchmark produced
  2,512 rows by 45 columns for 2016-09-29 through 2026-09-28. There were 2,327
  eligible observations, 376 condition-days (14.97% of all rows; 16.16% of eligible
  rows), and 117 events. Example entries: 2017-06-27, 2017-06-29, 2017-09-08;
  the last cached entry was 2026-08-10. No infinite thresholds occurred; flags were
  boolean and every event was a condition-day. No generated outputs were saved.
- Interpretation: Frequency was not effectively zero or close to universal. This
  is descriptive implementation validation only; no future returns were inspected,
  no parameters were tuned, and no predictive/performance conclusion was drawn.
- Limitations: Correlated components, inclusive ties, interrupted eligibility,
  overlapping episodes, history dependence, survivorship, and revised adjusted
  data remain. Incomplete rows break runs; later entries do not prove a distinct
  economic episode. Inputs must retain correct upstream feature/benchmark provenance.
- Next step: Predefine empirical evaluation splits, baselines, and after-close
  timing/cost assumptions before separately implementing outcome evaluation or
  backtesting. DipScore and all later strategy/execution milestones remain unstarted.

## 2026-09-30 — Outcome machinery and frozen EXP-001 protocol

- Research question: What happens after V1 events under explicit, reproducible
  next-open entry assumptions, and how does it compare with ordinary observations?
- Hypothesis: Unchanged V1 candidates may carry information beyond unconditional
  stock and matched SPY returns; profitable outcomes are not assumed.
- Work performed: Established the 293-test baseline. Added independent forward
  outcomes at 1/3/5/10/20 bars; first-hit target/stop/time exits; conservative daily
  ambiguity and observed-open gap semantics; two-sided costs; and independent versus
  non-overlapping ticker modes. Added chronological partitions, full-window censoring,
  baselines, descriptive metrics, date-cluster block-bootstrap intervals, subgroup
  summaries, and an offline runner with snapshot hashes and fixed configuration.
  Preserved existing data/feature/signal APIs. Recorded ADR-012/013.
- Result: Full suite with warnings treated as errors: 419 passed (293 existing,
  73 backtest/runner tests, 53 metric tests). Synthetic known paths, missing windows,
  split boundaries, ticker isolation, causal signal preservation, cost arithmetic,
  paired benchmark dates, and bootstrap reproducibility pass. No market outcomes
  have yet been inspected; EXP-001's protocol is recorded before its first run.
- Interpretation: Implementation behavior is tested, not predictive performance.
  Do not mistake dependent event samples or variable-holding trades for regular
  portfolio returns. Trade excursions on intraday exit bars are labelled envelopes.
- Limitations: Boundary censoring, daily fill ambiguity, illustrative costs,
  incomplete calendars, survivor selection, and revised adjusted-data inputs remain.
  Bootstrap blocks only approximate dependence; small groups have undefined intervals.
- Next step: Run the frozen offline EXP-001 once and report every split, including
  negative results, without tuning or choosing favorable parameters/horizons.

## 2026-09-30 — EXP-001 completed and interrupted-session work recovered

- Research question: Does the first fixed V1 specification show favorable outcomes
  relative to ordinary stock observations and matched SPY intervals?
- Hypothesis: The predeclared EXP-001 hypothesis is unchanged; positive absolute
  returns alone do not demonstrate incremental signal value or profitability.
- Recovery: Found outcome machinery already committed in `accbaa0` and metrics,
  tests, runner, and frozen protocol in `801b8ff`. Only the EXP-001 results draft
  was uncommitted. Preserved all implementation, tests, input caches, and parameters.
  The global Python test attempt failed collection because PyArrow was absent;
  using the existing project `.venv` resolved the environment mismatch without
  changing dependencies. The complete recovered suite passed: 419 tests, with
  warnings treated as errors.
- Work performed: Reviewed execution and metric semantics and deterministic
  coverage; completed experiment documentation and updated milestone status,
  README, and ADR-014. Retained all five stocks, all five horizons, both trade
  modes, and the three/four-component subgroups. See EXP-001 for exact snapshot
  hashes, chronological boundaries, counts, and full tables.
- Reproduction: Reran the unchanged offline experiment with warnings treated as
  errors. All 87 table data rows matched programmatic results at displayed precision.
  Corrected only the prose pre-censoring non-signal totals for validation/test to
  2,180 / 2,120; the draft had used completed one-bar counts. Rerun JSON and its
  local table audit remain ignored under `data/`. No network or cache refresh occurred.
- Result: Research / validation / test contain 358 / 97 / 109 events. Ten-bar
  gross event means are 1.331% / 2.664% / 1.784%; unconditional means are 1.022% /
  1.876% / 1.050%, and matched-SPY means are 0.555% / 1.423% / 0.740%. Several
  shorter-horizon comparisons are unfavorable. Non-overlapping barrier trades
  average 0.221% / 1.684% / 0.019% net under the fixed costs. Test win rate is
  47.297%, median -0.773%, and profit factor 1.007. Test MSFT and GOOGL sequences
  compound to -34.135% and -23.281%; research AMZN compounds to -40.502%.
- Interpretation: Mixed historical evidence, without established significance of
  baseline differences or a robust profitable edge. Four components are not
  uniformly better than three. The historical test partition is consumed by
  reporting. No thresholds, holding periods, barriers, or stocks were selected
  after observing results; negative findings remain part of the record.
- Limitations: Five surviving mega-caps, revised adjusted data, dependent overlapping
  windows, small subgroup samples, approximate bootstrap coverage, daily execution
  ambiguity, full-window censoring, illustrative costs, and absent portfolio
  allocation/liquidity accounting. Trade-close drawdown omits intratrade losses.
- Next step: Recommend separately pre-registered robustness / walk-forward work,
  broader point-in-time universe construction, and stronger fresh-holdout methodology.
  This next milestone has not begun; no parameter optimization was performed.

## 2026-09-30 — EXP-002 registration and robustness infrastructure

- Question: Does frozen V1 behavior generalize across previously unevaluated stocks
  and repeated historical OOS folds, rather than just the original five stocks?
- Work: Confirmed 419 baseline tests. Registered and pushed `ff6a99d` before
  acquiring new stock histories. The dated official OEF source gives 101 equity
  symbols, 95 after excluding EXP-001 issuers including GOOG. Added static/interval
  eligibility, expanding annual folds, fold-bounded evaluation, causal SPY regimes,
  cross-sectional distributions, frequency, concentration and a reproducible runner.
- Implementation: Vectorized existing forward endpoints/extrema to support larger
  controls. The entire cached EXP-001 report is exactly unchanged, excluding code
  revision/dirty metadata. Feature/signal modules remain hash-guarded and unchanged.
- Acquisition: Initial sandbox access prevented yfinance's local database from
  opening, before any histories were returned. Retried acquisition with required
  access; each missing symbol then received at most two attempts. Obtained 74 stock
  caches; 21 symbols failed existing OHLC range validation. Kept the failures,
  made no replacements, and did not relax ingestion checks. SPY cache is unchanged.
  The infrastructure failure is not treated as evidence of missing market history.
- Interpretation: No EXP-002 market outcomes inspected at this infrastructure
  stage. Deterministic synthetic tests cover boundary censoring, prefix equivalence,
  ticker isolation, membership, causal regimes, diagnostics and replay.
- Validation: Complete suite with warnings treated as errors: 467 passed.
  `pip check` found no broken requirements. Synthetic replay produced identical
  metadata and all artifact hashes. Generated cache/results paths are ignored.
- Next: Validate and commit the implementation, then run/report the registered
  experiment without changing the protocol or selecting favorable stocks/parameters.

## 2026-10-01 — EXP-002 results verified and documented

- Work: Completed the September 30 real-data run and independent offline replay
  on clean revision `70a85ef`. Both metadata files and all 27 artifact hashes match
  exactly. Audited 23,389 completed forward outcomes directly against cached OHLC,
  and 7,780 completed records across both trade modes for costs and fold boundaries.
  Added a hash-verifying documentation renderer and generated the experiment tables.
- Universe: 95 requested current OEF stocks after excluding EXP-001 issuers; 74
  usable, 21 excluded by existing malformed-OHLC checks, with no replacements.
  Six annual folds cover 2021-01-04 through 2026-09-28, with expanding history from
  2016-09-29 and partial 2026. Current membership and adjusted vintages are not PIT.
- Frequency/results: 4,825 events. Ten-bar pooled gross mean is 1.066%, versus
  0.741% unconditional and 0.822% matched SPY. Event/benchmark differences have not
  been established as statistically significant. Only 36/74 ticker paired excess
  means are positive, so the registered directional breadth criterion fails even
  though event means beat both controls in 5/6 folds.
- Barriers: Non-overlapping pooled mean net 0.510%, median 0.329%, win rate 52.462%,
  PF 1.230, across 3,128 trades. Five folds and 52/74 tickers have positive net
  means, satisfying the separate descriptive sign criterion. But 2022 mean net
  is -0.246%; 22 ticker expectancies are negative, including BLK -1.805%, LOW
  -1.142%, and DIS -0.922%. No loss or failed criterion has been hidden.
- Concentration/regimes: Top five account for 26.328% of positive ticker net
  contributions and 41.373% of positive ten-bar excess contributions. Neither
  exceeds the registered 50% diagnostic flag. Above/below-SPY-200-day regimes
  average 0.423%/0.790% non-overlapping net, with different absolute/excess event
  behavior. Three components average 1.157% at ten bars versus four at 0.768%.
- Integrity: The preregistration text and configuration remain unchanged; feature,
  signal, evaluation and aggregation sources match hashes recorded during the run.
  Only reporting/tests/documentation were finished after observing outcomes. EXP-001
  remains intact, including its near-zero test result. Generated datasets and
  outputs remain ignored. No parameters or sample members were selected afterward.
- Final validation: 468 tests passed with warnings treated as errors (419 existing
  plus 49 new deterministic tests). `pip check` reports no broken requirements.
  The renderer's document check passes; both real-data runs retain identical
  metadata/artifact hashes. Generated/private/cache files are not tracked.
- Interpretation/limitations: Positive pooled descriptive behavior persists, but
  broad ticker-level incremental evidence fails the declared criterion. Survivor
  and data-quality selection, revised prices, unequal histories, dependence,
  approximate intervals, daily fills and absent portfolio/capacity accounting
  prohibit claims of causal alpha or validated future profitability.
- Next (recommendation only): Historical universe/data-quality audit and a separately
  pre-registered prospective paper-signal archive. Both experiments' inspected
  history is consumed. No support/scoring/ML, optimization, scanner or archive
  implementation began in this milestone.

## 2026-10-01 - EXP-003 registration

Recovered clean main at f21d193; all 468 baseline tests pass with warnings as
errors. Recorded hashes of 144 existing cache/results/config/source files locally
before further work (the generated manifest gives the authoritative count).
Registered a separate 21-ticker diagnostic audit and manual 95-name prospective
archive protocol, preserving all consumed EXP-001/EXP-002 evidence. No new
diagnostic data or prospective record has been acquired at registration.

## 2026-10-01 - Diagnostic preservation implementation

Added immutable local publication, raw-response quarantine, exact OHLC discrepancy
measurements and an offline replayable audit runner. Sixteen deterministic tests
pass with warnings as errors, including one-ULP rejection, rejected-row/vintage
preservation, integrity/conflict checks and interruption recovery. No ingestion
tolerance or strategy code changed. New diagnostic acquisition follows the pushed
registration; results are recorded separately.

## 2026-10-01 - Session timing foundation

Added exchange-calendars 4.13.2 (and its required dependencies) to obtain explicit
XNYS sessions, holidays, early closes and DST-aware next-open deadlines. Twenty
offline timing tests pass, including stale/late/replay/correction gates and missing
run expectations. This dependency serves calendar correctness, not signal changes.
The first diagnostic attempt failed yfinance database access in the sandbox; all
21 failures remain in data/exp003/diagnostic. An approved infrastructure retry
uses data/exp003/diagnostic_authorized without replacing the failed records.

## 2026-10-01 - Manual archive foundation

Added the frozen-config manual collector, immutable run/input/result/receipt records,
atomic session/version reservations, explicit failures/non-events, post-publication
timing classification, integrity/replay and interrupted-run recovery. Raw and
validated snapshots use a separate ignored content-addressed archive. Corrections
remain separate from the original holdout. No scheduler or outcomes are implemented.
The intermediate full suite passed 528 tests with warnings as errors; seven further
archive edge cases bring its targeted suite to 31 passing tests. Publication that
crosses the next open is late; old caches remain retrospective. The first eligible
signal session (October 1) has not closed at implementation time, so no genuinely
prospective observations can yet be collected.

## 2026-10-01 - EXP-003 audit findings and final verification

- Registration: `8c55fbc` was pushed before acquisition. Configuration and the
  standalone protocol remain byte-equivalent after newline normalization.
- Diagnostic evidence: the separately approved retry preserved 21 new adjusted
  response vintages, 52,752 rows total. Twelve tickers have 29 one-spacing OHLC
  close-boundary violations; nine now pass. Original rejected responses were not
  preserved, so original offending values/causes cannot be reconstructed. No
  tolerance, price, row, original exclusion or frozen experiment output changed.
- Reporting: Added a hash-verifying audit renderer, all-21-name table with dates,
  numerical observations and performance-independent remediation recommendation.
  Retained full raw frames and exact row-level OHLC values in ignored quarantine.
- Provenance: Re-read the original OEF CSV and confirmed its hash and exact
  101-to-95 selection. Documented symbol/share-class/spin-off limitations, and
  official S&P, Norgate and CRSP historical-data options. Norgate documents no
  announcement dates and omits temporary inclusions. No paid dataset, contract
  or PIT membership reconstruction was acquired or claimed.
- Archive exercise: Consumed September 28 replay preserved all 95 names, with
  74 available decisions and 21 unavailable inputs. All are retrospective, none
  prospective. Offline decision replay matches; repeating the same run ID keeps
  the original receipt and one run intent. The October 1 signal session had not
  closed, so no genuine prospective collection was possible during this task.
- Final hardening: Direct archive run creation now checks the registered config,
  as well as the CLI guard, preventing callers from bypassing the frozen settings.
  Four parameter-drift regressions pass. No change to V1 semantics or registration.
- Validation: **539 tests passed**, complete suite with warnings as errors.
  `pip check` reports no broken requirements. A targeted earlier rerun encountered
  a Windows pytest temporary-directory permission failure; approved access
  resolved it without test changes. Both experiment documentation checks pass.
  Verified all 144 frozen cache/result/config/source files unchanged, and the
  entire prior EXP-001/EXP-002 registry content remains an unchanged prefix.
- Git/data policy: Raw diagnostics, archived market bytes and generated records
  remain ignored. Only data/results directory placeholders are tracked. Frozen
  data, feature, signal, universe, backtest and robustness modules are unchanged.
- Interpretation/next: This milestone establishes an auditable manual collection
  foundation, not profitability, PIT reconstruction or prospective outcome
  validation. Recommend separately authorized adjustment-arithmetic/identity and
  historical-membership validation, and operation of the registered manual archive
  without peeking at performance. No next research milestone was begun.

## 2026-10-01 - Local quantitative research terminal

- Scope: Added an offline React/TypeScript/Vite research frontend with all eleven
  requested views. Recharts supplies baseline, fold, distribution, frequency,
  price, feature and component-activation visualizations; plain CSS provides a
  restrained desktop layout and collapsible mobile navigation.
- Data: Added `scripts/build_dashboard_data.py` with frozen-protocol checks,
  original artifact/snapshot verification, immutable generation files and atomic
  manifest publication. The browser verifies hashes and loads one ticker at a
  time. Python remains the quantitative source of truth; no market acquisition,
  parameter search or new performance specification is run by the adapter.
- Explorer: Preserved EXP-002 observation/event/trade files and existing EXP-001
  APIs provide 79 ticker histories across the experiments. EXP-001 saved summary
  statistics remain unchanged. Signal-time values and prior thresholds are
  separated from future outcomes; decision-panel charts end at the selected
  session. All censoring and both trade modes remain visible.
- Integrity: Failed EXP-002 breadth, negative 2022, losing stocks, static-universe
  selection and all 21 OHLC exclusions remain visible. The archive shows the 95
  historical replay records separately from zero genuinely prospective records,
  with non-events, unavailable inputs, provenance and unpopulated outcome fields.
  No collection, outcome scoring or repair occurs in the frontend.
- Validation: Full backend suite **546 passed**, warnings treated as errors;
  **9 frontend tests passed**; TypeScript and production build passed. Two browser
  scenarios exercised all views, real artifact loading, ticker/component/feature
  selection, archive separation and mobile navigation. Desktop/mobile screenshots
  were inspected. `pip check` passed. A Windows preview-process teardown stalled
  after both browser scenarios passed; the identified preview process was stopped
  explicitly, with no application or research failure.
- Preservation: Verified all 144 files in the existing frozen inventory unchanged,
  plus the complete experiment registry and frozen config/research modules against
  recovered commit `00e8fc4`. Generated exports, datasets, screenshots, dependencies
  and build outputs remain ignored. No research result is copied into TypeScript.
- Decision/next: The local presentation foundation is complete. See ADR-019 and
  `docs/DASHBOARD.md`. Recommend a separately reviewed publication subset and
  artifact-availability workflow if a public recruiter-facing demo is desired.
  No API, deployment, live scanner, trading integration or next research milestone
  has begun.

## 2026-10-01 - Short research briefs and learning support

- Request: Make the site easier to understand, with less text and smaller,
  meaningful commits. Saved these preferences in `AGENTS.md`.
- Change: Experiments opens with four short answers. Full records and detailed
  tables are optional. Overview adds a three-step learning path; metric names
  open explanations and labeled examples on desktop and mobile. Rates such as
  win rate are unsigned rather than colored as positive returns.
- Integrity: Failed breadth, negative 2022, losing stocks and missing prospective
  evidence stay visible. Source statistics, protocols and V1 are unchanged.
- References: NN/g's progressive disclosure, Our World in Data's explanatory
  charts and Portfolio Visualizer's comparisons informed the presentation.
  Source links and design choices are in `docs/DASHBOARD.md`.
- Scope: Added `docs/RESEARCH_FOCUS.md`, a proposal for an independently defined
  tech/AI group with other sectors as controls. It is not a pre-registration or
  a new backtest; consumed historical data would remain exploratory evidence.
- Validation: Ten frontend tests and three real-data browser scenarios pass;
  TypeScript and production builds pass. Desktop/mobile briefs were inspected.
  No Python research calculation or generated market data was changed.

## 2026-10-02 - ATR exit and EV research preparation

- Request: Explore stock-aware exits and use expected value clearly.
- Change: Added an ATR(14)-scaled barrier calculator and made net EV's win/loss
  probabilities, average win/loss and break-even win rate explicit.
- Integrity: Registered a fixed candidate grid in EXP-004. No exit candidates
  were evaluated or selected; consumed validation/test outcomes remain untouched.
  V1's +10% / -7% / 10-bar configuration is unchanged.
- Next: Only consider prospective comparison at EXP-003's scheduled review gate,
  with separate authorization to attach/evaluate outcomes.
