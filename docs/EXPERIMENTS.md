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
