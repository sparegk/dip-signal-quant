# Experiment registry

Do not infer performance from implementation tests. Add an entry for every
significant experiment, including negative results.
Define splits and selection rules before inspecting the final test period.

## Experiment template

- Experiment ID: EXP-NNN
- Date:
- Hypothesis:
- Universe (membership source, selection date, survivorship limitations):
- Time period:
- Split: in-sample / validation / out-of-sample (exact boundaries)
- Data snapshot / source / retrieval time / adjustment convention:
- Code commit / environment / random seed (if applicable):
- Signal definition and information availability:
- Parameters and parameter-selection procedure:
- Transaction-cost assumptions (fees, spread, slippage):
- Entry, exit, and execution timing assumptions:
- Number of signals / trades:
- Return (definition and benchmark):
- Hit rate:
- Expectancy:
- Sharpe (frequency, annualization, risk-free assumption):
- Sortino (target return and annualization):
- Maximum drawdown:
- Profit factor:
- Average holding period:
- Result / conclusion:
- Limitations / failed variants / multiple-testing considerations:
- Artifacts and next step:

Use `not measured` for unavailable metrics. Never invent results or silently
exclude failed configurations.

## EXP-001 — DipSignal V1 baseline evaluation

Protocol fixed 2026-09-30, before inspecting this experiment's outcomes.

- Hypothesis: V1 event dates may carry information about subsequent returns beyond
  ordinary stock behavior and matched SPY returns. No profitable edge is assumed.
- Universe: existing cached AAPL, MSFT, NVDA, AMZN, GOOGL; SPY benchmark. Convenience
  selection of current survivors, not historical point-in-time membership.
- Signal: unchanged V1 defaults (252-bar comparison, 126 valid prior values,
  20th-percentile tail, at least three components and complete-row readiness).
- Outcomes: next observed open to entry-inclusive 1/3/5/10/20-bar closes, MFE/MAE;
  independent event observations; identical unconditional/non-condition controls;
  SPY open-to-close returns on exact stock entry/end dates.
- Splits: earliest 60%, next 20%, final 20% of unique observed stock session dates;
  common boundaries across tickers, assigned by signal date. Full horizon/max-hold
  windows must remain in the split. No endpoint liquidation or selective early exits.
- Exit illustration: +10% target, -7% stop, 10 bars; conservative same-bar policy,
  observed-open gap fills. Evaluate independent and non-overlapping-per-ticker modes.
- Costs: report gross and net at 1 bp commission plus 5 bp slippage per side;
  fees on slipped notionals. These are illustrative, not fitted assumptions.
- Uncertainty: 2,000 circular block resamples, seed 42, 20 observed signal-date
  clusters per block, 95% percentile intervals. At least 40 clusters required.
- Subgroups: research/validation/test and existing component counts 3 versus 4
  at the 10-bar horizon. All five horizons reported, without selecting a winner.
- Metrics/interpretation: see BACKTESTING.md. No pooled event/trade portfolio
  compounding, Sharpe, Sortino, or daily drawdown will be fabricated. Single-ticker
  sequential compounding is hypothetical, not pooled portfolio performance.
- Selection procedure: one fixed specification. No parameter optimization,
  threshold changes, feature weighting, or strategy selection from test results.
- Reproduction: `python -m scripts.evaluate_v1`; offline JSON with input hashes,
  exact dates, settings, revision, audit counts, and metrics. No data files written.
- Results: first fixed-specification evaluation completed and reproduced without
  parameter changes during session recovery; full findings follow.

### First run and reproducibility

Run date: 2026-09-30. Frozen execution revision: `801b8ff7beabb0dd7c07a75c6126d897aa478ee9`;
working tree clean during the run. Python 3.14.3, pandas 3.0.6,
NumPy 2.5.3; existing pinned environment unchanged. No network calls,
cache refreshes, output data files, parameter changes, or optimizations occurred.
The reference runner took roughly four minutes on this Windows environment;
large-universe throughput has not been established.

Recovery verification on 2026-09-30 reran the unchanged evaluation code in the
same `.venv` with warnings treated as errors and provider downloading disabled.
All 87 table data rows below matched the rerun JSON at the displayed precision,
including snapshot hashes, boundaries, counts, baselines, and trade metrics.
The rerun correctly reports a dirty working tree because documentation was being
finished; execution code remains at the frozen revision. Its stdout was saved to
ignored `data/exp001-verification.json` for local verification, with the local
table audit in `data/audit_exp001.py`; neither artifact is versioned. A prose-only
count error was corrected: validation/test non-signal totals before censoring
had been copied from their completed one-bar counts. No result table changed.

All six cached snapshots contain 2,512 daily observations spanning **2016-09-29
through 2026-09-28**. Source: yfinance 1.7.0, auto-adjusted OHLC, provider volume;
retrieved 2026-09-29 at 21:52:36–21:52:39 UTC. Current adjusted vintages are not
point-in-time execution prices. Preserve these local snapshots to reproduce results.

| Ticker | Parquet SHA-256 |
| --- | --- |
| AAPL | `e583dc4b54132b0ad8465b43ed6ab993146cc107dad516f1c7318ffdd02fd6da` |
| MSFT | `4a7301456ca0d8832c3206d3aad7168f9e51b2911fcceb5df4d4d766c530638d` |
| NVDA | `21529bd621c9f6cc11fef1e701048923eb5a92b1e14be327f5d8b0d290fad406` |
| AMZN | `d09d5d94d537a062fd690b05ec7fae9909d2324e227a3e8176e9480d1c73cd81` |
| GOOGL | `45396b2648fa2a4911445a35006a526539cc9abbb075c6383f7830bbd00b1477` |
| SPY | `e8e087e4b22fad51e7aa9fffa9c4b6fca4fe82dcdda9e59032ae599cc6c2b873` |

### Chronological samples

| Split | Signal-date start | Signal-date end | Stock rows | Ready rows | V1 events |
| --- | --- | --- | --- | --- | --- |
| research | 2016-09-29 | 2022-09-23 | 7535 | 6610 | 358 |
| validation | 2022-09-26 | 2024-09-24 | 2510 | 2510 | 97 |
| test | 2024-09-25 | 2026-09-28 | 2515 | 2515 | 109 |

The 564 events are not independent trades. Research has 185 initial warm-up rows
per stock; later splits retain past feature/threshold history. The final split is
historical out-of-sample for this predeclared specification, now **consumed by
reporting**; do not optimize on it or call it untouched in future research.

### Fixed-horizon event outcomes

Returns are gross entry-open to horizon-close fractions expressed as percentages;
entry day counts as day 1. CI/SE use the fixed date-cluster block bootstrap, not
IID event assumptions. Intervals concern event means, **not** event-minus-baseline
differences or claims of alpha. N is the number of complete same-split outcomes.

| Split | Bars | N | Excluded | Mean | Median | Std | Bootstrap SE | 95% CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| research | 1 | 354 | 4 | 0.294% | 0.313% | 2.347% | 0.139% | [0.042%, 0.584%] |
| research | 3 | 354 | 4 | 0.377% | 0.378% | 4.054% | 0.232% | [-0.094%, 0.819%] |
| research | 5 | 353 | 5 | 0.386% | 0.368% | 5.647% | 0.319% | [-0.262%, 0.965%] |
| research | 10 | 349 | 9 | 1.331% | 1.788% | 7.315% | 0.539% | [0.251%, 2.363%] |
| research | 20 | 345 | 13 | 2.341% | 2.451% | 9.851% | 1.259% | [-0.167%, 4.802%] |
| validation | 1 | 97 | 0 | 0.069% | 0.220% | 1.909% | 0.134% | [-0.196%, 0.322%] |
| validation | 3 | 97 | 0 | 1.027% | 0.807% | 3.697% | 0.294% | [0.512%, 1.639%] |
| validation | 5 | 97 | 0 | 1.140% | 1.515% | 4.616% | 0.498% | [0.273%, 2.144%] |
| validation | 10 | 96 | 1 | 2.664% | 2.108% | 6.262% | 0.445% | [1.796%, 3.565%] |
| validation | 20 | 92 | 5 | 5.751% | 4.360% | 9.087% | 1.013% | [3.811%, 7.758%] |
| test | 1 | 109 | 0 | 0.093% | -0.017% | 2.114% | 0.191% | [-0.269%, 0.457%] |
| test | 3 | 109 | 0 | 0.188% | 0.067% | 3.655% | 0.402% | [-0.525%, 1.014%] |
| test | 5 | 109 | 0 | 0.542% | 0.639% | 5.146% | 0.716% | [-0.804%, 1.976%] |
| test | 10 | 109 | 0 | 1.784% | 1.672% | 5.606% | 0.742% | [0.400%, 3.286%] |
| test | 20 | 107 | 2 | 2.954% | 2.163% | 9.282% | 1.461% | [-0.060%, 5.644%] |

| Split | Bars | Win rate | Average MFE | Average MAE | Event-return profit factor |
| --- | --- | --- | --- | --- | --- |
| research | 1 | 58.192% | 1.817% | -1.565% | 1.436 |
| research | 3 | 54.237% | 3.241% | -2.917% | 1.284 |
| research | 5 | 53.541% | 4.185% | -4.003% | 1.214 |
| research | 10 | 59.312% | 5.908% | -5.476% | 1.618 |
| research | 20 | 62.899% | 8.438% | -7.005% | 1.915 |
| validation | 1 | 54.639% | 1.453% | -1.416% | 1.100 |
| validation | 3 | 57.732% | 3.077% | -2.509% | 2.056 |
| validation | 5 | 60.825% | 3.989% | -3.206% | 1.909 |
| validation | 10 | 62.500% | 6.086% | -4.419% | 3.107 |
| validation | 20 | 76.087% | 9.746% | -5.731% | 6.786 |
| test | 1 | 49.541% | 1.444% | -1.443% | 1.146 |
| test | 3 | 52.294% | 2.957% | -2.849% | 1.141 |
| test | 5 | 52.294% | 4.219% | -3.770% | 1.307 |
| test | 10 | 60.550% | 5.911% | -4.926% | 2.265 |
| test | 20 | 58.879% | 8.973% | -6.572% | 2.376 |

Expectancy equals the reported arithmetic mean (zero returns included). MFE/MAE
here describe the entire fixed window, not the separate barrier model. No event
returns are compounded into an alleged portfolio curve.

### Baseline comparisons

Controls use identical next-open timing, eligibility, horizons, and full-window
censoring. Unconditional means all ready rows; non-signal means ready and
condition=false. Controls have different ticker/date composition and overlapping
windows. SPY is paired to each event's exact stock endpoints; all completed events
in this run had matched benchmark endpoints, so paired N equals event N above.

| Split | Bars | Event mean | Eligible N | Eligible mean | Non-signal N | Non-signal mean | Matched SPY mean | Mean event minus SPY |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| research | 1 | 0.294% | 6605 | 0.030% | 5457 | -0.005% | 0.085% | 0.209% |
| research | 3 | 0.377% | 6595 | 0.243% | 5449 | 0.220% | -0.040% | 0.417% |
| research | 5 | 0.386% | 6585 | 0.465% | 5442 | 0.422% | -0.099% | 0.485% |
| research | 10 | 1.331% | 6560 | 1.022% | 5425 | 0.946% | 0.555% | 0.776% |
| research | 20 | 2.341% | 6510 | 2.150% | 5398 | 2.151% | 1.647% | 0.693% |
| validation | 1 | 0.069% | 2505 | 0.108% | 2175 | 0.108% | -0.000% | 0.069% |
| validation | 3 | 1.027% | 2495 | 0.499% | 2165 | 0.484% | 0.373% | 0.655% |
| validation | 5 | 1.140% | 2485 | 0.902% | 2155 | 0.868% | 0.620% | 0.520% |
| validation | 10 | 2.664% | 2460 | 1.876% | 2133 | 1.724% | 1.423% | 1.241% |
| validation | 20 | 5.751% | 2410 | 3.922% | 2098 | 3.766% | 3.194% | 2.557% |
| test | 1 | 0.093% | 2510 | 0.052% | 2115 | 0.019% | -0.019% | 0.112% |
| test | 3 | 0.188% | 2500 | 0.274% | 2105 | 0.142% | 0.088% | 0.100% |
| test | 5 | 0.542% | 2490 | 0.497% | 2095 | 0.307% | 0.242% | 0.301% |
| test | 10 | 1.784% | 2465 | 1.050% | 2070 | 0.922% | 0.740% | 1.044% |
| test | 20 | 2.954% | 2415 | 2.100% | 2023 | 2.081% | 1.360% | 1.595% |

Unconditional ready-row counts before horizon censoring are 6,610 / 2,510 / 2,515
(research / validation / test). Non-signal counts before censoring are 5,458 /
2,180 / 2,120. Complete-control counts above vary by horizon; the runner reports
all exclusions. Baseline uncertainty is available in its JSON output.

### Illustrative barrier trades

Target +10%, stop -7%, maximum 10 bars; conservative same-bar policy. Gross excludes
costs; net includes 1 bp commission and 5 bp slippage on **each side**. Each row
below pools descriptive trade outcomes, not allocated portfolio capital returns.
Independent means every fully observable event; non-overlapping means one active
trade per ticker without same-bar capital recycling.

| Split | Mode | Completed | Gross mean | Net mean / expectancy | Net median | Net std | Net win rate | Profit factor | Mean holding bars |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| research | independent | 349 | 0.582% | 0.461% | 0.793% | 6.515% | 53.582% | 1.177 | 7.91 |
| research | non_overlapping | 222 | 0.341% | 0.221% | 0.547% | 6.595% | 52.703% | 1.080 | 7.87 |
| validation | independent | 96 | 1.505% | 1.383% | 1.636% | 6.015% | 55.208% | 1.719 | 8.55 |
| validation | non_overlapping | 65 | 1.806% | 1.684% | 2.013% | 6.213% | 58.462% | 1.869 | 8.49 |
| test | independent | 109 | 0.310% | 0.189% | 0.721% | 6.295% | 51.376% | 1.073 | 8.21 |
| test | non_overlapping | 74 | 0.139% | 0.019% | -0.773% | 6.366% | 47.297% | 1.007 | 8.11 |

| Split | Mode | TP rate | SL rate | Time-exit rate | Mean MFE envelope | Mean MAE envelope | Excluded / skipped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| research | independent | 15.473% | 29.513% | 55.014% | 5.058% | -4.412% | split_boundary: 9 |
| research | non_overlapping | 15.766% | 30.631% | 53.604% | 5.042% | -4.458% | overlap: 127; split_boundary: 9 |
| validation | independent | 14.583% | 17.708% | 67.708% | 5.184% | -3.743% | split_boundary: 1 |
| validation | non_overlapping | 18.462% | 16.923% | 64.615% | 5.532% | -3.712% | overlap: 31; split_boundary: 1 |
| test | independent | 14.679% | 25.688% | 59.633% | 5.079% | -4.388% | none |
| test | non_overlapping | 16.216% | 27.027% | 56.757% | 4.973% | -4.380% | overlap: 35 |

No completed trade in this snapshot hit both barriers in the same bar; synthetic
coverage verifies the conservative/optimistic policies. Trade excursion columns
are the documented exit-bar envelopes, not precisely identified intraday pre-fill
extrema. Rejected candidates remain in the audit, not silently removed from counts.
Pooled cumulative return, Sharpe, Sortino, and portfolio drawdown are **not measured**:
no regular-period allocated equity series exists. Do not annualize these trade means.

### Single-ticker non-overlapping sequences

The following cumulative net returns assume each ticker independently reinvests
all capital on each accepted trade, with zero idle-cash return. Drawdown is measured
only at trade closes, including initial capital. These are not annualized returns,
not daily mark-to-market drawdowns, and not a combined portfolio.

| Split | Ticker | Trades | Net mean | Hypothetical cumulative net | Trade-close max drawdown |
| --- | --- | --- | --- | --- | --- |
| research | AAPL | 41 | 0.103% | -5.254% | -25.864% |
| research | MSFT | 44 | 1.298% | 65.875% | -21.711% |
| research | NVDA | 51 | 0.559% | 12.563% | -41.829% |
| research | AMZN | 42 | -1.050% | -40.502% | -49.595% |
| research | GOOGL | 44 | 0.074% | -3.943% | -40.876% |
| validation | AAPL | 15 | 1.651% | 25.321% | -7.327% |
| validation | MSFT | 11 | 3.122% | 38.726% | -4.559% |
| validation | NVDA | 13 | 0.373% | 0.260% | -17.888% |
| validation | AMZN | 14 | 3.212% | 51.526% | -9.012% |
| validation | GOOGL | 12 | 0.045% | -0.630% | -11.019% |
| test | AAPL | 13 | 1.431% | 17.010% | -16.842% |
| test | MSFT | 16 | -2.511% | -34.135% | -34.135% |
| test | NVDA | 16 | 1.019% | 13.091% | -26.569% |
| test | AMZN | 15 | 2.025% | 31.011% | -16.048% |
| test | GOOGL | 14 | -1.693% | -23.281% | -33.747% |

### Existing-component subgroups (10-bar event outcomes)

Descriptive only: do not choose component weights, cutoffs, or scores from this table.

| Split | Active components | N | Date clusters | Mean | Median | 95% CI |
| --- | --- | --- | --- | --- | --- | --- |
| research | 3 | 255 | 192 | 0.993% | 1.647% | [-0.197%, 2.202%] |
| research | 4 | 94 | 76 | 2.248% | 2.754% | [0.604%, 3.772%] |
| validation | 3 | 73 | 63 | 2.894% | 2.688% | [1.905%, 3.737%] |
| validation | 4 | 23 | 21 | 1.933% | 0.231% | undefined (<40 clusters) |
| test | 3 | 82 | 71 | 1.566% | 1.531% | [0.193%, 3.074%] |
| test | 4 | 27 | 26 | 2.446% | 1.999% | undefined (<40 clusters) |

### Interpretation, including unfavorable findings

- Positive event means alone do not demonstrate signal value or profitability.
  At 10 bars, event means exceeded both unconditional and matched-SPY means in
  this sample, but the reported intervals are not tests of those differences.
- Comparisons are not uniformly favorable: research 5-bar events averaged 0.386%
  versus 0.465% unconditional and 0.422% on non-condition dates; validation 1-bar
  events lagged both stock controls; test 3-bar events lagged unconditional rows.
- The illustrative barrier rule retained much less of the fixed-horizon test-period
  mean. Non-overlapping test trades averaged **0.019% net** (about 1.92 bp), with
  a **47.3% win rate**, **-0.773% median**, and **1.007 profit factor**. This is
  close to zero under just one uncalibrated cost assumption, not a robust edge.
- Heterogeneity matters: test MSFT and GOOGL hypothetical sequential net returns
  were -34.135% and -23.281%; research AMZN was -40.502% with -49.595% trade-close
  drawdown. These losses are retained, not excluded as failed stocks.
- More active components were not uniformly better: validation four-component
  events averaged less than three-component events, and its 21 date clusters (26
  in test) were too few for the predeclared default interval calculation.
- The five current survivors, overlapping events, changing market regimes, small
  effective sample sizes, adjusted-data revisions, full-window censoring, daily
  execution ambiguity, and missing allocation/liquidity modelling prevent strong
  causal or investability conclusions. Multiple reported horizons/subgroups are
  descriptive, not independently confirmed discoveries. Bootstrap dependence and
  coverage assumptions remain unverified.
- No parameters were changed after seeing results, and no negative variant or
  stock was discarded. The run is one fixed specification, not an optimized winner.

Next step: pre-register robustness and walk-forward evaluation on a broader
point-in-time universe with fresh holdout data and better execution/capital
accounting. This does not authorize or begin parameter optimization.

## EXP-002 — Pre-registered cross-sectional robustness and walk-forward evaluation

Protocol date: 2026-09-30. **Registered before downloading/evaluating the new
stock histories. Results pending.** The protocol and `config/exp002.json` must be
committed and pushed before the main evaluation. Subsequent results are appended;
the protocol is not rewritten after observing outcomes. Genuine bug corrections
must identify their effect and affected runs.

### Question and frozen specification

Does the previously specified DipSignal V1 exhibit similar behavior across a
substantially broader set of stocks and repeated historical out-of-sample periods?
This is robustness testing, not optimization. EXP-001's historical holdout is
consumed; its mixed findings, including 0.019% mean net non-overlapping test return,
remain evidence. New names offer fresher **cross-sectional**, not untouched future
temporal evidence; the research concept has already been informed by history.

- Freeze existing feature definitions/default windows, V1 components and rising-edge
  semantics, 252 prior positions, minimum 126 valid values, quantile 0.20, and three
  required components with full readiness. Configuration includes normalized-source
  SHA-256 checks for the feature/signal modules. No grids, tuning, or stock selection
  based on outcomes. Implementation improvements may preserve numerical semantics.
- Entry: next observed same-ticker open after signal-date close. Horizons 1/3/5/10/20
  observed bars, including entry bar. Gross open-to-close returns and window MFE/MAE.
- Barriers: +10% TP, -7% SL, maximum 10 bars; conservative same-bar ordering and
  observed-open gap fills. Report independent and non-overlapping-per-ticker modes.
- Costs: 1 bp commission and 5 bp adverse slippage each side, fees on slipped
  notionals; preserve EXP-001 formula. No alternative cost/exit selection.
- Controls: all ready eligible stock dates and ready condition=false dates with
  identical timing/censoring; SPY exact stock entry/end endpoints, no filling.

### Universe and data rules

**Current-constituent / static-universe robustness test; survivorship bias remains.**
Use all rows classified US Equity in the official [iShares OEF holdings CSV](https://www.ishares.com/us/products/239723/ishares-s-p-100-etf/latest-holdings.csv)
as of 2026-09-29, retrieved 2026-09-30. OEF tracks the S&P 100; this is a transparent
current mega-cap/liquidity proxy, not a historical liquidity screen or an exact
historical index reconstruction. The source has 101 equity tickers. Normalize
space/dot share-class separators to dash (BRK B -> BRK-B), sort alphabetically,
and exclude AAPL/MSFT/NVDA/AMZN/GOOGL plus GOOG (same already-inspected issuer).
SPY is benchmark-only. **95 requested primary stocks**, all retained if data permit;
no replacements for failures, no selection using charts/returns, no EXP-001 rerun
in the primary pool. The compact source symbol list, source hash and fixed settings
are versioned in `config/exp002.json`; raw source and market files remain ignored.

Request [2016-09-29, 2026-09-29), matching the EXP-001 date span. Reuse existing
validated market-data/cache APIs, preserve SPY's existing vintage, and download
only missing caches. Do not refresh inputs automatically. Record hashes, retrieval
provenance, actual coverage, and all source/holdout/data exclusions. Up to two
download attempts per missing symbol before outcomes; no outcome-driven retries.
Shorter histories enter only when V1 has causal readiness. Usable means at least
one ready eligible OOS observation; no-event stocks remain in frequency and
distribution denominators with undefined outcome means. Report each fold's
coverage and no-ready-history exclusions; do not require survival/full history
in every fold or fill missing bars. Corrupt caches and benchmark failures raise.

Provide a reusable static universe and interval schema (`ticker`, inclusive
`start_date`, exclusive `end_date`, null end=open-ended). Validate disjoint ordered
intervals. Membership gates **signal-date eligibility**, not the price history;
calculate unchanged signals on all available prior history before masking selected
observations. Do not invent a new rising edge at admission. An accepted event's
path may extend after membership removal; using future removal to select events
would be retrospective selection. Fold boundaries still censor full windows.
An interval file alone does not establish genuine point-in-time provenance.

### Expanding chronological folds and boundary safety

Use SPY's observed dates inside the fixed range as the common fold calendar.
First OOS calendar year begins at the first January 1 on/after four calendar years
from the first supplied benchmark date. This yields 2021, 2022, 2023, 2024, 2025,
and available 2026 through 2026-09-28. Each fold uses all history from 2016-09-29
through its last observed session; history ends strictly before its OOS start.
Features/thresholds update causally within OOS as new completed bars arrive;
there is no fitted model or parameter selection. Later folds expand past history.
Exact observed start/end dates are saved with the outputs. Label 2026 partial.

Require the entire horizon or configured maximum barrier window within the fold,
even if a barrier could hit early. Censor near-boundary and terminal observations;
never borrow the next fold's prices or fabricate liquidation. Non-overlap restarts
at fold boundaries because all accepted prior-fold positions already exited.
No supervised fitting occurs, so no extra arbitrary training embargo is introduced;
future fitted models would require purging labels/embargo separately.

### Predeclared analyses, metrics and interpretation

- Report all five horizons by fold and pooled OOS, and per ticker. Include counts,
  exclusions, mean/median/std, win rate, expectancy, profit factor, MFE/MAE, paired
  benchmark counts/returns, and stock controls. Pooled values weight observations;
  additionally report equal-ticker means, median, quartiles/IQR, positive/negative/
  zero/undefined counts. Ticker distributions include event-minus-SPY means and
  non-overlapping net expectancy, so positive gross returns are not the only test.
- Report both barrier modes by fold and pooled OOS, and per ticker; TP/SL/time
  distribution, holding bars, gross/net moments, profit factor and excursion
  envelopes. No pooled compounding, Sharpe, Sortino, or portfolio drawdown.
- Concentration: sum equal-notional net trade return contributions by ticker in
  non-overlapping mode (not capital returns). Report top five positive contributors'
  share of total positive ticker contributions, top five absolute-contribution
  share, total positive/negative contributions, and all ticker sums. Repeat the
  descriptive calculation for 10-bar stock-minus-SPY event contributions. Avoid
  unstable percentages dividing by near-zero aggregate net results. Do not remove
  losing names or construct an ex-winner strategy.
- Frequency: per ticker/calendar-year and fold counts of observed, eligible,
  ready, condition, and event dates, condition/ready and condition/eligible fractions,
  event count distribution, plus 252*events/ready observations as an exposure-scaled
  frequency. Label partial years/history; zero events are explicit.
- Regime: signal-date SPY close >= its trailing 200-observed-close mean versus
  below; include the completed current close, require all 200 observations, and
  retain `unknown` when unavailable. Exact-date joins only, no filling. Report all
  horizons and both barrier modes by regime, pooled and by fold. No other regime
  thresholds or optimized classifiers. Report 3-versus-4 components at 10 bars.
- Uncertainty: preserve EXP-001 circular blocks of 20 distinct observation-date
  clusters, 2,000 draws, seed 42, 95% percentile intervals, minimum 40 clusters.
  Same-day stocks stay together; pooled dates are sorted. These are intervals for
  means, not formal tests of baseline differences. Cross-ticker/serial dependence,
  structural breaks, multiple comparisons, and circular pooled blocks spanning
  fold gaps limit inference; no claim of calibrated significance.
- Interpretation criteria fixed now: call evidence directionally broad only if
  10-bar event means exceed both unconditional and matched-SPY means in a strict
  majority of available folds, and a strict majority of tickers with defined
  paired excess means are positive. Assess barrier stability separately using
  strict-majority positive fold and ticker net expectancy; report magnitudes and
  every negative fold/ticker regardless. Top-five positive contribution share above
  50% flags concentration. These are descriptive diagnostics, not optimized cutoffs,
  statistical rejection rules, or profitability certification. Sparse intervals,
  mixed signs, small cost margins, or large regime differences weaken conclusions.

### Reproduction, artifacts and future holdout

Implement `python -m scripts.evaluate_exp002` with frozen configuration, optional
explicit download mode, and offline replay. Save fold/ticker/regime/frequency/
distribution/concentration summaries, event/trade/control ledgers, exclusions,
input provenance, protocol/config/code hashes and deterministic output hashes
under ignored `results/exp_002/`. Compact documentation is generated from these
outputs; no large generated data is committed. Verify repeat runs with identical
cached inputs/configuration, including synthetic offline integration tests.

After EXP-002, designate all inspected symbols/dates as consumed. A later approved
paper-signal archive must preserve timestamped after-close signals, input vintages,
universe eligibility, code/config hashes, and planned next-open execution before
outcomes exist. Corrections append versions rather than overwrite history. Set a
future evaluation schedule/criteria before accumulating outcomes; do not tune on
that holdout or simulate future observations. This task documents the policy only;
it does not implement a scanner/archive or begin the next model milestone.

### EXP-002 completion and interpretation — 2026-09-30

The preregistration above is retained verbatim as the historical protocol. The
experiment is now complete; **no protocol or V1 parameter was changed after
observing EXP-002 outcomes**. The main evaluation and an independent offline replay
ran on clean revision `70a85efb9712af584e21e8b2fa2dd38438d81f3e`; metadata and all
27 artifact hashes match exactly. An independent cached-OHLC audit checked all
23,389 completed horizon outcomes and all 7,780 completed trade cost/boundary
records. The latter count includes both modes, not disjoint economic trades.
Generated tables below are reproduced by `python -m scripts.report_exp002`;
`--check-doc docs/EXPERIMENTS.md` checks them against hash-verified artifacts.

The source list requested 95 names. Seventy-four passed ingestion and had ready
OOS observations; 21 failed the existing open/close-inside-high/low checks. The
failed names and reasons are reported below. They were not replaced, repaired,
or excluded based on performance. These data-quality exclusions can themselves
change sample composition. GEV and SNDK begin in 2024 and 2025; PLTR and UBER also
have shorter histories. Later admission follows causal readiness rather than a
full-history survival requirement. The old SPY snapshot was preserved; new stock
snapshots have their own retrieval vintages, recorded and hashed in metadata.

Findings against the **predeclared** descriptive criteria:

- Ten-bar event means exceed unconditional stock means in 6/6 folds and matched
  SPY in 5/6. However, only **36/74 tickers (48.649%)** have positive mean paired
  excess returns. The strict-majority ticker requirement fails: the registered
  definition of directionally broad evidence is **not met**. The median ticker
  ten-bar excess is -0.014%, despite the positive pooled excess of 0.244%.
- Positive gross ten-bar means occur in 66/74 tickers; this is not equivalent to
  incremental signal value. Pooled event mean is 1.066% versus 0.741% unconditional
  and 0.822% matched SPY. The event-mean interval [0.532%, 1.635%] is not a test of
  either baseline difference. One-bar event and unconditional means are essentially
  equal; the median ticker paired excess is negative at one and three bars too.
- The fixed non-overlapping barrier produces **0.510% mean net**, 0.329% median,
  52.462% win rate, and 1.230 profit factor across 3,128 trades. It is not near zero
  in this pooled sample under the registered costs. Five of six fold means and
  52/74 ticker means are positive, satisfying the separate descriptive barrier
  sign criteria. This is a different universe/period from EXP-001, not a tuned
  improvement to EXP-001 or proof of profitable implementation.
- Magnitudes are unstable: 2022 net mean is **-0.246%**, median -0.902%, and profit
  factor 0.921. Twenty-two ticker net expectancies are negative. Examples retained
  in the complete ticker table: BLK -1.805%, LOW -1.142%, DIS -0.922%, COST -0.641%,
  NFLX -0.634%. No unfavorable ticker/year is discarded.
- Top-five shares of positive ticker contributions are 26.328% for net trades and
  41.373% for ten-bar event excess, below the registered 50% concentration flag.
  This does not negate the weak breadth of excess returns or unequal histories.
  Contribution sums are equal-notional diagnostics, not portfolio capital returns.
- Regimes differ: above/below SPY's causal 200-day mean, ten-bar event means are
  0.926%/1.526% and matched-SPY excesses 0.276%/0.139%. Non-overlapping net means
  are 0.423%/0.790%. The below-average regime's stronger absolute returns do not
  imply greater incremental signal value; dates, volatility and stock composition
  differ. No regime-based filter was selected.
- More components again are not uniformly better: pooled three-component ten-bar
  event mean is 1.157%, versus 0.768% for four components. No weighting/threshold
  change follows. Small ticker histories/subgroups, especially recent listings,
  require caution despite the larger overall sample.
- Frequency is material but variable: 4,825 events; condition/ready rates range
  11.461%–18.371% across folds. Exposure-scaled frequency ranges 9.842–13.971 events
  per 252 ready rows across folds. Across usable tickers, total events range 10–85,
  median 67; these counts include different lengths of available history.

Scientific interpretation: some positive historical descriptive behavior survives
broader sampling, particularly the barrier's pooled net mean, but the registered
cross-sectional excess-breadth criterion fails and 2022/ticker losses remain.
No significance of baseline outperformance, causal alpha, stable future edge,
capacity, or investability is established. All 2021–2026 folds and new names have
now been inspected. Survivor/current-size selection, 21 OHLC exclusions, revised
adjusted vintages, dependent windows, approximate bootstrap coverage, daily order
ambiguity, full-window censoring and uncalibrated execution/capital assumptions
remain material limitations. No portfolio return or daily drawdown is measured.

Recommended next milestone, **not begun**: audit the excluded data and secure
better historical membership/identity and execution inputs, then pre-register a
prospective immutable paper-signal archive and review schedule for genuinely unseen
temporal evidence. Review this evidence before authorizing DipScore, support, ML,
feature selection, optimization, or a live scanner. Preserve both EXP-001's mixed
results and EXP-002's failed breadth criterion.

<!-- EXP002_GENERATED_TABLES_START -->

### EXP-002 results generated from verified artifacts

Execution revision: `70a85efb9712af584e21e8b2fa2dd38438d81f3e`; dirty tree: `False`.
Registered in `ff6a99d`; configuration SHA-256:
`7a7f18b8e0bd2bb22433fbf64a60431c6e70819374d0d0b3a328f444834bd2b2`.

Requested 95; usable 74; excluded 21.
Current-constituent static universe; all retained outcomes are reported without parameter selection.

#### Expanding folds and signal frequency

| Fold | History end | OOS start | OOS end | Ready tickers | Ready rows | Events | Condition / ready | Events / 252 ready |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | 2020-12-31 | 2021-01-04 | 2021-12-31 | 72 | 18024 | 803 | 16.006% | 11.227 |
| 2022 | 2021-12-31 | 2022-01-03 | 2022-12-30 | 72 | 18072 | 910 | 16.622% | 12.689 |
| 2023 | 2022-12-30 | 2023-01-03 | 2023-12-29 | 72 | 18000 | 703 | 11.461% | 9.842 |
| 2024 | 2023-12-29 | 2024-01-02 | 2024-12-31 | 73 | 18152 | 793 | 15.635% | 11.009 |
| 2025 | 2024-12-31 | 2025-01-02 | 2025-12-31 | 74 | 18287 | 857 | 15.333% | 11.810 |
| 2026 | 2025-12-31 | 2026-01-02 | 2026-09-28 | 74 | 13690 | 759 | 18.371% | 13.971 |

All folds share history origin 2016-09-29. The final fold may be partial. Readiness counts
include warm-up/history restrictions; no-event and absent ticker-folds remain in frequency.csv.

#### All fixed-horizon event outcomes by fold (gross)

| Fold | Bars | N | Excluded | Mean | Median | MFE | MAE | 95% mean CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | 1 | 801 | 2 | 0.092% | 0.066% | 1.233% | -1.182% | [-0.097%, 0.290%] |
| 2021 | 3 | 801 | 2 | 0.311% | 0.284% | 2.292% | -2.123% | [-0.074%, 0.709%] |
| 2021 | 5 | 800 | 3 | 0.550% | 0.504% | 3.059% | -2.747% | [0.028%, 1.113%] |
| 2021 | 10 | 785 | 18 | 0.949% | 0.927% | 4.508% | -3.859% | [0.188%, 1.773%] |
| 2021 | 20 | 748 | 55 | 2.199% | 1.916% | 6.762% | -4.879% | [1.159%, 3.291%] |
| 2022 | 1 | 909 | 1 | -0.146% | -0.117% | 1.680% | -1.821% | [-0.364%, 0.113%] |
| 2022 | 3 | 905 | 5 | 0.109% | -0.223% | 3.222% | -3.370% | [-0.513%, 0.875%] |
| 2022 | 5 | 900 | 10 | -0.010% | 0.064% | 4.157% | -4.474% | [-1.061%, 1.233%] |
| 2022 | 10 | 889 | 21 | 0.034% | 0.132% | 5.841% | -6.259% | [-1.779%, 1.954%] |
| 2022 | 20 | 865 | 45 | 0.323% | -0.005% | 8.235% | -8.605% | [-2.705%, 3.170%] |
| 2023 | 1 | 701 | 2 | 0.013% | 0.014% | 1.126% | -1.193% | [-0.163%, 0.183%] |
| 2023 | 3 | 700 | 3 | 0.391% | 0.272% | 2.405% | -2.062% | [0.035%, 0.731%] |
| 2023 | 5 | 700 | 3 | 0.675% | 0.617% | 3.232% | -2.673% | [0.053%, 1.312%] |
| 2023 | 10 | 693 | 10 | 1.341% | 0.971% | 4.797% | -3.558% | [0.400%, 2.283%] |
| 2023 | 20 | 675 | 28 | 3.200% | 1.925% | 7.761% | -4.646% | [0.991%, 5.449%] |
| 2024 | 1 | 788 | 5 | -0.060% | 0.013% | 1.050% | -1.197% | [-0.197%, 0.095%] |
| 2024 | 3 | 770 | 23 | -0.013% | -0.063% | 2.094% | -2.232% | [-0.403%, 0.402%] |
| 2024 | 5 | 767 | 26 | 0.468% | 0.442% | 3.017% | -2.847% | [-0.249%, 1.310%] |
| 2024 | 10 | 742 | 51 | 1.569% | 0.798% | 5.135% | -3.820% | [0.267%, 3.187%] |
| 2024 | 20 | 690 | 103 | 3.028% | 2.137% | 8.058% | -4.847% | [1.326%, 4.778%] |
| 2025 | 1 | 852 | 5 | 0.178% | 0.171% | 1.531% | -1.525% | [-0.066%, 0.467%] |
| 2025 | 3 | 849 | 8 | 0.397% | 0.276% | 2.891% | -2.658% | [-0.175%, 0.974%] |
| 2025 | 5 | 847 | 10 | 0.700% | 0.623% | 3.927% | -3.385% | [-0.188%, 1.480%] |
| 2025 | 10 | 838 | 19 | 1.476% | 1.167% | 5.705% | -4.545% | [0.108%, 2.643%] |
| 2025 | 20 | 807 | 50 | 2.537% | 1.853% | 8.536% | -6.397% | [-0.528%, 5.502%] |
| 2026 | 1 | 749 | 10 | 0.172% | 0.067% | 1.622% | -1.506% | [-0.046%, 0.410%] |
| 2026 | 3 | 738 | 21 | 0.404% | 0.320% | 3.250% | -2.861% | [-0.124%, 0.895%] |
| 2026 | 5 | 727 | 32 | 0.737% | 0.413% | 4.412% | -3.680% | [0.012%, 1.411%] |
| 2026 | 10 | 705 | 54 | 1.213% | 0.158% | 6.561% | -5.205% | [-0.058%, 2.582%] |
| 2026 | 20 | 648 | 111 | 2.138% | 0.917% | 9.752% | -7.070% | [-0.530%, 4.833%] |

#### Ten-bar baseline comparisons by fold

| Fold | Event | Unconditional | Non-signal | Matched SPY | Event minus SPY |
| --- | --- | --- | --- | --- | --- |
| 2021 | 0.949% | 0.920% | 0.856% | 1.101% | -0.153% |
| 2022 | 0.034% | -0.477% | -0.621% | 0.010% | 0.024% |
| 2023 | 1.341% | 1.147% | 1.077% | 1.105% | 0.237% |
| 2024 | 1.569% | 0.952% | 0.884% | 1.226% | 0.343% |
| 2025 | 1.476% | 1.030% | 0.942% | 0.839% | 0.637% |
| 2026 | 1.213% | 0.914% | 0.855% | 0.816% | 0.398% |

#### Pooled OOS event and baseline results

| Bars | N | Event mean | Median | Unconditional | Non-signal | Matched SPY | Excess | 95% event-mean CI |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 4800 | 0.038% | 0.039% | 0.038% | 0.037% | 0.027% | 0.011% | [-0.055%, 0.140%] |
| 3 | 4763 | 0.261% | 0.166% | 0.200% | 0.176% | 0.249% | 0.013% | [0.052%, 0.499%] |
| 5 | 4741 | 0.504% | 0.449% | 0.361% | 0.316% | 0.404% | 0.100% | [0.178%, 0.868%] |
| 10 | 4652 | 1.066% | 0.728% | 0.741% | 0.663% | 0.822% | 0.244% | [0.532%, 1.635%] |
| 20 | 4433 | 2.167% | 1.475% | 1.577% | 1.437% | 1.572% | 0.594% | [1.123%, 3.223%] |

#### Pooled event excursions and dispersion

| Bars | MFE | MAE | Std | Win rate |
| --- | --- | --- | --- | --- |
| 1 | 1.385% | -1.418% | 1.980% | 51.062% |
| 3 | 2.709% | -2.578% | 3.774% | 52.530% |
| 5 | 3.649% | -3.337% | 4.899% | 55.748% |
| 10 | 5.433% | -4.594% | 6.901% | 55.675% |
| 20 | 8.163% | -6.162% | 9.913% | 58.155% |

#### Frozen barrier outcomes, including costs

| Fold | Mode | N | Gross mean | Net mean | Net median | Win rate | PF | Holding bars | TP/SL/time counts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | independent | 785 | 0.628% | 0.508% | 0.524% | 53.885% | 1.282 | 9.145 | 58/114/613 |
| 2022 | independent | 889 | -0.157% | -0.277% | -0.783% | 46.794% | 0.910 | 7.643 | 152/306/431 |
| 2023 | independent | 693 | 1.120% | 0.998% | 0.813% | 57.431% | 1.661 | 9.185 | 67/78/548 |
| 2024 | independent | 742 | 0.866% | 0.745% | 0.577% | 54.178% | 1.394 | 8.929 | 89/111/542 |
| 2025 | independent | 838 | 0.900% | 0.779% | 0.666% | 54.057% | 1.379 | 8.476 | 112/170/556 |
| 2026 | independent | 705 | 0.445% | 0.325% | -0.219% | 48.227% | 1.129 | 8.054 | 130/173/402 |
| 2021 | non_overlapping | 500 | 0.648% | 0.527% | 0.521% | 54.600% | 1.294 | 9.212 | 35/74/391 |
| 2022 | non_overlapping | 607 | -0.127% | -0.246% | -0.902% | 47.282% | 0.921 | 7.504 | 110/213/284 |
| 2023 | non_overlapping | 468 | 1.039% | 0.917% | 0.692% | 56.197% | 1.569 | 9.145 | 48/56/364 |
| 2024 | non_overlapping | 514 | 0.752% | 0.631% | 0.411% | 53.891% | 1.318 | 8.765 | 67/84/363 |
| 2025 | non_overlapping | 560 | 0.827% | 0.706% | 0.561% | 53.571% | 1.329 | 8.338 | 79/121/360 |
| 2026 | non_overlapping | 479 | 0.812% | 0.691% | 0.037% | 50.313% | 1.283 | 7.962 | 98/115/266 |
| all | independent | 4652 | 0.610% | 0.490% | 0.308% | 52.279% | 1.226 | 8.544 | 608/952/3092 |
| all | non_overlapping | 3128 | 0.630% | 0.510% | 0.329% | 52.462% | 1.230 | 8.449 | 437/663/2028 |

Costs are 1 bp commission plus 5 bp slippage per side. These are pooled trade statistics,
not allocated portfolio returns; no pooled Sharpe, Sortino or portfolio drawdown is claimed.

#### Cross-sectional distribution (requested-ticker accounting)

| Kind | Bars | Metric | Positive | Negative | Zero | Undefined | Median | Q25 / Q75 | Positive / defined |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| event | 1 | mean | 38 | 36 | 0 | 21 | 0.005% | -0.116% / 0.143% | 51.351% |
| event | 1 | mean_excess_return | 30 | 44 | 0 | 21 | -0.043% | -0.109% / 0.125% | 40.541% |
| event | 3 | mean | 56 | 18 | 0 | 21 | 0.225% | 0.019% / 0.549% | 75.676% |
| event | 3 | mean_excess_return | 35 | 39 | 0 | 21 | -0.032% | -0.221% / 0.222% | 47.297% |
| event | 5 | mean | 59 | 15 | 0 | 21 | 0.444% | 0.114% / 0.801% | 79.730% |
| event | 5 | mean_excess_return | 40 | 34 | 0 | 21 | 0.037% | -0.287% / 0.305% | 54.054% |
| event | 10 | mean | 66 | 8 | 0 | 21 | 0.778% | 0.301% / 1.486% | 89.189% |
| event | 10 | mean_excess_return | 36 | 38 | 0 | 21 | -0.014% | -0.439% / 0.568% | 48.649% |
| event | 20 | mean | 70 | 4 | 0 | 21 | 1.764% | 1.169% / 3.077% | 94.595% |
| event | 20 | mean_excess_return | 45 | 29 | 0 | 21 | 0.265% | -0.414% / 1.341% | 60.811% |
| trade | 10 | net_expectancy | 52 | 22 | 0 | 21 | 0.455% | -0.067% / 1.022% | 70.270% |

Across usable tickers: events total median 67.0, Q25/Q75 60.0/72.0, min/max 10/85.
Across ready ticker-years (partial years included), events per 252 ready rows median 11.088, Q25/Q75 9.000/14.112.

#### Performance concentration (equal-notional return sums)

| Measure | Positive sum | Negative sum | Net sum | Top-five positive share | Top-five absolute share | Top positive contributors |
| --- | --- | --- | --- | --- | --- | --- |
| event_excess_10 | 22.479 | -11.133 | 11.346 | 41.373% | 27.669% | PLTR, DELL, AVGO, ANET, MU |
| net_trades | 19.614 | -3.672 | 15.941 | 26.328% | 22.176% | ANET, MU, PANW, PLTR, DHR |

#### Ticker non-overlapping barrier results (all candidate tickers retained)

| Ticker | Trades | Net mean | Net median | PF |
| --- | --- | --- | --- | --- |
| ABBV | 39 | 0.674% | 1.333% | 1.496 |
| ACN | 48 | 0.294% | 0.616% | 1.107 |
| ADBE | 48 | -0.415% | -0.499% | 0.844 |
| AMAT | 48 | -0.005% | -1.042% | 0.999 |
| AMD | 59 | -0.271% | -2.351% | 0.921 |
| AMGN | 44 | 0.618% | 1.193% | 1.406 |
| AMT | 37 | -0.414% | 0.013% | 0.831 |
| ANET | 48 | 2.368% | 2.602% | 2.055 |
| AVGO | 51 | 1.109% | 1.396% | 1.403 |
| AXP | 40 | 0.985% | -0.220% | 1.487 |
| BA | 42 | -0.385% | -1.166% | 0.868 |
| BAC | 40 | 0.325% | 0.796% | 1.156 |
| BKNG | 45 | -0.028% | -0.176% | 0.989 |
| BLK | 39 | -1.805% | -1.995% | 0.426 |
| BNY | 42 | 1.383% | 2.646% | 1.823 |
| BRK-B | 39 | 1.557% | 1.594% | 3.196 |
| C | 40 | 1.080% | 1.116% | 1.573 |
| CAT | 43 | 0.334% | 0.409% | 1.140 |
| COF | 47 | 1.237% | 0.996% | 1.488 |
| COP | 36 | 1.264% | 0.997% | 1.616 |
| COST | 31 | -0.641% | 0.081% | 0.655 |
| CRM | 49 | -0.200% | -1.356% | 0.938 |
| CSCO | 45 | 0.667% | 0.502% | 1.486 |
| CVX | 38 | 0.669% | 0.244% | 1.369 |
| DE | 45 | 1.242% | 0.957% | 1.729 |
| DELL | 40 | 1.323% | 1.931% | 1.564 |
| DHR | 43 | 1.814% | 2.257% | 2.133 |
| DIS | 43 | -0.922% | -1.419% | 0.583 |
| EMR | 46 | 0.975% | 1.215% | 1.519 |
| FDX | 43 | -0.288% | -0.501% | 0.887 |
| GD | 36 | 0.767% | 0.825% | 1.778 |
| GE | 48 | 1.015% | 1.912% | 1.495 |
| GEV | 17 | 2.625% | 6.648% | 2.064 |
| GILD | 42 | 0.644% | 0.619% | 1.449 |
| GM | 50 | 0.501% | 0.058% | 1.188 |
| GS | 44 | 0.597% | 0.986% | 1.330 |
| IBM | 40 | 1.117% | 0.359% | 1.778 |
| INTC | 45 | 0.748% | 1.364% | 1.261 |
| INTU | 48 | 0.927% | 0.461% | 1.358 |
| ISRG | 50 | 0.865% | 0.088% | 1.360 |
| JPM | 37 | 0.204% | 0.113% | 1.123 |
| LIN | 42 | 0.576% | 1.503% | 1.447 |
| LLY | 39 | 0.209% | -0.685% | 1.084 |
| LOW | 44 | -1.142% | -1.563% | 0.587 |
| LRCX | 47 | 0.226% | 0.240% | 1.064 |
| MA | 40 | -0.077% | -0.192% | 0.949 |
| MCD | 35 | -0.214% | -0.197% | 0.856 |
| MDLZ | 44 | 0.489% | -0.001% | 1.419 |
| MDT | 43 | 0.082% | -0.893% | 1.042 |
| META | 42 | -0.379% | -1.066% | 0.889 |
| MRK | 42 | 0.451% | 0.981% | 1.263 |
| MS | 42 | 1.321% | 1.456% | 1.783 |
| MU | 48 | 2.310% | 1.056% | 2.174 |
| NEE | 44 | -0.126% | -0.363% | 0.942 |
| NFLX | 40 | -0.634% | -1.527% | 0.812 |
| NOW | 46 | 1.559% | -0.120% | 1.586 |
| ORCL | 40 | -0.540% | -1.603% | 0.820 |
| PANW | 41 | 2.621% | 5.608% | 2.091 |
| PEP | 45 | 0.222% | 0.341% | 1.190 |
| PG | 40 | -0.036% | 0.146% | 0.973 |
| PLTR | 42 | 2.532% | 5.579% | 1.813 |
| PM | 41 | 1.024% | 0.622% | 1.752 |
| SBUX | 47 | -0.100% | 0.407% | 0.954 |
| SCHW | 44 | 0.458% | 1.063% | 1.225 |
| SNDK | 9 | 3.818% | 9.868% | 2.333 |
| TMO | 44 | 0.244% | 0.108% | 1.135 |
| TMUS | 38 | -0.180% | -1.128% | 0.915 |
| TSLA | 50 | 0.116% | -4.820% | 1.030 |
| UBER | 53 | 0.313% | -0.968% | 1.111 |
| UNH | 42 | -0.097% | 0.670% | 0.953 |
| USB | 47 | 0.353% | -0.285% | 1.161 |
| V | 39 | 0.541% | 0.661% | 1.464 |
| WFC | 35 | 0.398% | -0.343% | 1.156 |
| WMT | 38 | 0.028% | 0.679% | 1.016 |

#### SPY 200-day-average regimes: pooled event outcomes

| Regime | Bars | N | Event mean | Unconditional | Matched SPY | Excess | 95% event-mean CI |
| --- | --- | --- | --- | --- | --- | --- | --- |
| above | 1 | 3690 | 0.025% | 0.023% | 0.021% | 0.004% | [-0.060%, 0.113%] |
| above | 3 | 3657 | 0.163% | 0.165% | 0.160% | 0.003% | [-0.039%, 0.356%] |
| above | 5 | 3640 | 0.407% | 0.323% | 0.301% | 0.106% | [0.098%, 0.706%] |
| above | 10 | 3562 | 0.926% | 0.684% | 0.650% | 0.276% | [0.430%, 1.469%] |
| above | 20 | 3361 | 1.869% | 1.511% | 1.304% | 0.565% | [1.030%, 2.707%] |
| below | 1 | 1110 | 0.082% | 0.101% | 0.050% | 0.032% | [-0.207%, 0.419%] |
| below | 3 | 1106 | 0.586% | 0.353% | 0.541% | 0.045% | [-0.080%, 1.299%] |
| below | 5 | 1101 | 0.826% | 0.522% | 0.746% | 0.081% | [-0.245%, 1.979%] |
| below | 10 | 1090 | 1.526% | 0.978% | 1.387% | 0.139% | [-0.151%, 3.122%] |
| below | 20 | 1072 | 3.101% | 1.848% | 2.414% | 0.687% | [0.182%, 6.129%] |

#### Regime barrier outcomes

| Regime | Mode | Trades | Net mean | Win rate | PF |
| --- | --- | --- | --- | --- | --- |
| above | independent | 3562 | 0.450% | 52.134% | 1.224 |
| below | independent | 1090 | 0.621% | 52.752% | 1.229 |
| above | non_overlapping | 2388 | 0.423% | 51.968% | 1.204 |
| below | non_overlapping | 740 | 0.790% | 54.054% | 1.294 |

#### Ten-bar component subgroups (descriptive)

| Components | N | Mean | Median | 95% mean CI |
| --- | --- | --- | --- | --- |
| 3 | 3565 | 1.157% | 0.770% | [0.588%, 1.711%] |
| 4 | 1087 | 0.768% | 0.638% | [0.062%, 1.495%] |

#### Data/history exclusions (no replacement stocks)

| Ticker | Reason | Detail |
| --- | --- | --- |
| ABT | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| BMY | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| CMCSA | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| CVS | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| DUK | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| HD | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| JNJ | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| KO | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| LMT | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| MMM | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| MO | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| PFE | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| QCOM | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| RTX | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| SO | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| T | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| TXN | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| UNP | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| UPS | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| VZ | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |
| XOM | download_or_validation_failed | Malformed OHLC: open/close must lie within low/high |

All per-fold regimes, per-ticker horizons and controls, audit statuses and missing-history
ticker-folds are retained in the machine-readable artifacts. Mean intervals do not test
event-minus-baseline differences. Source membership, adjusted prices, daily fills,
data exclusions, dependent samples and uncalibrated costs limit interpretation.

<!-- EXP002_GENERATED_TABLES_END -->

## EXP-003 ? Registered data audit and prospective archive foundation

Protocol date: 2026-10-01. The full preregistration is in
[EXP003_PROTOCOL.md](EXP003_PROTOCOL.md), with frozen settings in
`config/exp003.json`. Part A audits all 21 OHLC exclusions and universe provenance;
Part B defines a separate forward preservation protocol effective 2026-10-01.
Commit and push registration before new diagnostic acquisition or collection.
No historical performance reevaluation or outcome scoring is authorized.
Results pending; append findings without rewriting the registered protocol.
