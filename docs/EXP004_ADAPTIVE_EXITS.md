# EXP-004 - Adaptive Exit Policy Research

**Historical evaluation complete; prospective confirmation pending.** Selected
exits improve EV versus V1, but time-only has higher EV and selected downside/R
metrics are worse. [Jump to recorded results](#exp-004-results-generated-from-verified-artifacts).

## Registered protocol (revision 2, 2026-10-02)

Question: **given the same frozen V1 event, which exit policy captures the rebound
while controlling downside?** Primary selection objective is mean net return per
completed trade (estimated EV), after 1 bp commission and 5 bp slippage per side.
Win rate is secondary. The +10% / -7% / 10-bar rule is a control, not an optimum.

This explicitly requested revision supersedes the unrun ATR-only registration
`cb4df97` before any candidate performance was calculated. Its original config
remains preserved. The new search space is frozen in `config/exp004.json`.
No disappointing result authorizes adding a candidate; new ideas belong to EXP-005.

### Candidate catalogue

There are **136 configurations**: 132 selectable candidates in three families,
plus four controls. Every candidate has an explicit ID and parameters in config.

- Fixed stop/target pairs (%): 2/4, 3/4, 3/6, 4/6, 4/8, 5/8, 5/10, 6/8,
  6/12, 7/8, 7/12, 8/10, 8/12, 8/15, 10/12, 10/15, 10/20, 12/15,
  12/20, 15/20. Twenty curated pairs avoid an unnecessarily large fixed grid.
- ATR: stops {0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4} crossed with targets
  {1, 1.5, 2, 2.5, 3, 4, 5}: 56 candidates.
- ATR/R: the same eight stops crossed with R {0.75, 1, 1.25, 1.5, 2,
  2.5, 3}: 56 candidates.
- Controls: 7%/10%, target-only 10%, stop-only 7%, and time-only.

ATR fractions use **ATR14 / close on the signal session**, independently of later
ATR values. Stops are clipped to [1%, 20%]; targets to [1%, 30%]. These fixed
safety bounds are not optimized. Family R multiplies the bounded stop by R, then
bounds the target; clipping can change the effective R ratio. Fractions are frozen
at signal time and anchored to the next observed open. Missing event ATR is an
explicit error, never a performance-based exclusion. Structure stops are deferred
to EXP-005 to limit this experiment's search space.

### Entries, selection and folds

Use the exact EXP-002 requested universe and its original validated snapshot
vintages: 95 requested, 74 usable, 21 original exclusions, with no repair or
replacement. Recompute frozen V1 features/signals from hash-verified inputs and
verify OOS event identities/counts against preserved EXP-002 event artifacts.
All policies use the same independent event entries at t+1 observed open.

Reuse `annual_folds`: expanding history from 2016-09-29, evaluating calendar
2021-2026 (2026 partial). For each fold, use only events whose entire 10-bar
window ends before the fold starts. Require 200 completed training trades.
Select maximum pooled training net EV; exact ties use ascending candidate ID.
Also select a winner separately within each family using the same rule.
Controls are comparisons, not selectable candidates. If the minimum fails,
use V1 and explicitly report fallback. Freeze IDs/parameters before OOS evaluation.
Never choose among policies using OOS performance.

The primary mode is independent events so exit-dependent position overlap cannot
change the comparison cohort. Secondary same-ticker non-overlapping streams use
the existing no-same-open-recycling rule and reset at each OOS fold. Their accepted
entry sets can differ by policy and must be labeled accordingly.

All outcomes require a complete 10-bar window inside the applicable boundary,
including cases where a barrier hits early. Reuse the existing gap-aware,
conservative stop-first engine; do not create another fill engine. Precomputed
independent ledgers may be reused only with a full-window maturity gate; deterministic
tests must compare gated ledgers with truncation-before-evaluation and verify that
changing OOS prices cannot change training selections.

These are fold-OOS results for the registered algorithm on **consumed historical
dates**, not untouched temporal validation. Prior research informed this question.
Later folds legitimately expand training to previously completed earlier folds;
the current fold's outcomes are never used to select its policy.

### Diagnostics and interpretation

Preserve every training candidate's EV, win rate, median, PF, average win/loss,
and secondary worst ticker trade-close drawdown. Show the nondominated EV/win-rate
frontier. A near-best region is within 5 bp EV of the family winner; flag a
plateau only with at least three such candidates and two grid-adjacent near-best
neighbors of that winner. This training diagnostic does not change selection.

Report selected IDs per fold; whole/family-selected OOS, four controls, per ticker,
fold consistency, and paired same-event EV differences. Existing date-grouped
20-event-date moving-block bootstrap (2,000 draws, seed 42) describes uncertainty;
it is not a multiple-testing correction or proof of alpha. Training winners are
optimistic estimates selected from 132 candidates.

Report actual stop/target mean, median, quartiles, min/max by policy/fold/ticker.
Net R = net return / initial stop fraction. No-stop controls have undefined R.
Pooled drawdown is undefined; report separately the distribution/worst value of
per-ticker non-overlapping, reinvested trade-close drawdowns (not daily portfolio
drawdown). No portfolio equity, Sharpe or Sortino is fabricated.

Efficiency uses signed gross realized return / full 10-bar MFE; zero MFE is
undefined. Also retain net capture, exit-path MFE/MAE, full-window MFE/MAE, and
remaining MFE beyond the exit-path envelope. Intraday sequencing remains unknown.
For stopped trades only, inspect highs **strictly after the exit session** through
the original tenth holding bar for recovery to entry +2%, +5%, +10%. These are
post-exit diagnostics, not attainable additional trades; they never enter selection.

### Prospective policy

**Prospective evaluation pending genuine paper-signal outcomes.** Replay does not
count. Archive records/outcomes are not altered or scored in this experiment.
Use the predeclared selection algorithm and freeze its training-derived policy
before future execution opportunities; do not choose a historical OOS winner as
the future policy. Review follows EXP-003's dates/coverage gate and requires a
separately authorized outcome evaluator. Preserve failed signals and missing data.

### Reproduction

```powershell
.\.venv\Scripts\python.exe -m scripts.evaluate_exp004
.\.venv\Scripts\python.exe -m scripts.report_exp004
```

The runner is offline, validates config/input/artifact hashes, records code and
environment, and writes ignored machine artifacts to `results/exp_004/`. Identical
cached inputs/config produce identical research artifact hashes. No cache refresh,
universe change, new signal, optimizer outside the grid, or live execution occurs.

Results will be appended after the registered pipeline passes deterministic tests.

## Completion verification and operation

583 tests passed with warnings treated as errors; `pip check` passed. The extended
default engine exactly reproduced the previous 7,597-event ledgers in both modes.
An independent audit checked 61,379 completed OOS records: entries, signal-time
fractions, fills/costs, window extrema, R and capture arithmetic; training choices
and original V1 OOS execution fields match. The raw cached engine `split` label
is `all`; the explicit fold/maturity gates designate the OOS cohorts.

Two real-data runs matched all 15 research artifact hashes, executable-source
hashes and input vintages. The initial `1be35db` run recorded a dirty tree while
the ignore-rule/test/log safeguard correction was pending; those changes did not
alter execution or selection. The replay on `a5fe4af` recorded a clean tree.
PowerShell log redirection tagged stderr progress as `NativeCommandError`; replay
completion was verified against the full metadata and artifact receipts.

All 374 preservation-inventory files and the previous experiment sections remain
unchanged. Generated snapshots/results are ignored. Reproduction requires the
original ignored EXP-002 caches/artifacts; a fresh provider download is a new
vintage and will fail the pinned hashes. The registered protocol/configuration
and candidate set remain unchanged after evaluation.

<!-- EXP004_RESULTS_START -->
## EXP-004 results (generated from verified artifacts)

Registered in `55a4c5b` before evaluation. Execution revision `1be35dbb4e6c4ac66678c7d86a31892e693108a1`; dirty tree: `True`.

**Training-selected pooled fold-OOS net EV: +0.754% versus V1 +0.490%; paired difference +0.264%.** Positive EV differences occur in 6/6 folds and 53/74 tickers. The time-only control has higher EV (+0.945%); selected EV in R is 0.059 versus V1 0.070, and worst-ticker drawdown is deeper. These reused historical periods do not establish future profitability.

136 configurations (132 searchable, 3 families, four controls); 95 requested / 74 usable tickers, with the original exclusions retained. Config SHA256: `b01cd9855668d0dcbe75e576d316bcca2215007462df25b0f796ea51e22e6c8a`. Primary mode uses the same independent event entries; secondary streams accept policy-dependent subsets.

### Decision questions

1. Net EV difference versus V1 is +0.264%; date-block bootstrap interval [+0.092%, +0.458%]. This is descriptive uncertainty, not a correction for model search.
2. Median-return difference: +0.342%.
3. Profit factor: 1.358 versus 1.226.
4. Win rate: +54.794% versus +52.279%.
5. Fifth-percentile trade return: -10.004% versus -7.112%; worst ticker secondary trade-close drawdown: -65.434% versus -58.722%. Risk measures can disagree.
6. Fold improvement: 6/6; selected policy loses money in 1/6 folds.
7. Positive paired ticker EV differences: 53/74; median ticker difference +0.214%.
8. Selected IDs: 5 distinct across 6 folds; 4 changes between folds.
9. Training plateau flags: 13/18 family/fold surfaces. Full surfaces/frontiers are retained, including losing configurations.
10. Median signed full-window MFE capture: 0.219 versus V1 0.144. Negative ratios remain included.
11. Post-stop recoveries are shown below with measurable-stop denominators. Different stop cohorts prevent interpreting a conditional recovery rate as a causal improvement.
12. Prospective evaluation pending genuine paper-signal outcomes. Archived classifications: `{'retrospective': 95}`; no prospective outcomes were evaluated.

### Primary selections by fold

| Fold | Selected ID | Train N | Train net EV | OOS net EV | V1 OOS EV | Difference |
| --- | --- | --- | --- | --- | --- | --- |
| 2021 | r_s3_r1 | 2748 | +0.724% | +0.636% | +0.508% | +0.128% |
| 2022 | r_s4_r1 | 3557 | +0.747% | -0.148% | -0.277% | +0.129% |
| 2023 | atr_s4_t2.5 | 4464 | +0.628% | +1.079% | +0.998% | +0.081% |
| 2024 | r_s4_r0.75 | 5178 | +0.717% | +1.026% | +0.745% | +0.281% |
| 2025 | r_s4_r1.5 | 5930 | +0.761% | +1.187% | +0.779% | +0.408% |
| 2026 | r_s4_r1.5 | 6819 | +0.811% | +0.904% | +0.325% | +0.579% |

### Training-selected winner within each family

| Fold | Family policy | Selected ID | Training EV | OOS EV |
| --- | --- | --- | --- | --- |
| 2021 | best_fixed | fixed_s10_t15 | +0.509% | +0.731% |
| 2021 | best_atr | atr_s3_t4 | +0.713% | +0.658% |
| 2021 | best_r_multiple | r_s3_r1 | +0.724% | +0.636% |
| 2022 | best_fixed | fixed_s15_t20 | +0.605% | -0.155% |
| 2022 | best_atr | atr_s4_t4 | +0.743% | -0.147% |
| 2022 | best_r_multiple | r_s4_r1 | +0.747% | -0.148% |
| 2023 | best_fixed | fixed_s15_t20 | +0.478% | +1.175% |
| 2023 | best_atr | atr_s4_t2.5 | +0.628% | +1.079% |
| 2023 | best_r_multiple | r_s4_r0.75 | +0.621% | +1.141% |
| 2024 | best_fixed | fixed_s15_t20 | +0.603% | +1.346% |
| 2024 | best_atr | atr_s4_t2.5 | +0.712% | +0.946% |
| 2024 | best_r_multiple | r_s4_r0.75 | +0.717% | +1.026% |
| 2025 | best_fixed | fixed_s15_t20 | +0.695% | +1.251% |
| 2025 | best_atr | atr_s4_t4 | +0.750% | +1.191% |
| 2025 | best_r_multiple | r_s4_r1.5 | +0.761% | +1.187% |
| 2026 | best_fixed | fixed_s15_t20 | +0.762% | +0.676% |
| 2026 | best_atr | atr_s4_t4 | +0.803% | +0.841% |
| 2026 | best_r_multiple | r_s4_r1.5 | +0.811% | +0.904% |

### Pooled independent event comparison

| Policy | N | Net EV | Median | Win rate | PF | Avg win | Avg loss | EV in R | Bars | TP/SL/time | Worst ticker trade-close DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| best_atr | 4652 | +0.737% | +0.662% | +54.858% | 1.350 | +5.176% | -4.658% | 0.057 | 9.269 | 681/363/3608 | -63.541% |
| best_fixed | 4652 | +0.811% | +0.592% | +54.450% | 1.388 | +5.333% | -4.593% | 0.058 | 9.802 | 115/174/4363 | -57.061% |
| best_r_multiple | 4652 | +0.763% | +0.620% | +54.729% | 1.362 | +5.245% | -4.654% | 0.059 | 9.376 | 558/363/3731 | -65.434% |
| stop_only | 4652 | +0.578% | +0.236% | +51.720% | 1.262 | +5.377% | -4.562% | 0.083 | 9.030 | 0/968/3684 | -58.722% |
| target_only | 4652 | +0.837% | +0.682% | +55.159% | 1.425 | +5.086% | -4.391% | undefined | 9.477 | 646/0/4006 | -71.731% |
| time_only | 4652 | +0.945% | +0.607% | +54.643% | 1.473 | +5.384% | -4.403% | undefined | 10.000 | 0/0/4652 | -66.102% |
| training_selected | 4652 | +0.754% | +0.650% | +54.794% | 1.358 | +5.218% | -4.656% | 0.059 | 9.324 | 611/363/3678 | -65.434% |
| v1_control | 4652 | +0.490% | +0.308% | +52.279% | 1.226 | +5.087% | -4.547% | 0.070 | 8.544 | 608/952/3092 | -58.722% |

### Secondary non-overlapping trade comparison

| Policy | N | Net EV | Median | Win rate | PF | Avg win | Avg loss | EV in R | Bars | TP/SL/time | Worst ticker trade-close DD |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| best_atr | 3004 | +0.715% | +0.641% | +54.727% | 1.335 | +5.202% | -4.709% | 0.055 | 9.228 | 459/249/2296 | -63.541% |
| best_fixed | 2980 | +0.826% | +0.577% | +54.463% | 1.386 | +5.450% | -4.703% | 0.059 | 9.781 | 79/117/2784 | -57.061% |
| best_r_multiple | 3002 | +0.745% | +0.616% | +54.697% | 1.349 | +5.266% | -4.714% | 0.057 | 9.340 | 364/249/2389 | -65.434% |
| stop_only | 3100 | +0.662% | +0.257% | +51.968% | 1.296 | +5.575% | -4.653% | 0.095 | 9.000 | 0/660/2440 | -58.722% |
| target_only | 2984 | +0.785% | +0.652% | +55.027% | 1.389 | +5.096% | -4.489% | undefined | 9.468 | 420/0/2564 | -71.731% |
| time_only | 2962 | +0.922% | +0.573% | +54.490% | 1.451 | +5.445% | -4.493% | undefined | 10.000 | 0/0/2962 | -66.102% |
| training_selected | 3003 | +0.740% | +0.627% | +54.745% | 1.347 | +5.246% | -4.712% | 0.057 | 9.288 | 400/249/2354 | -65.434% |
| v1_control | 3128 | +0.510% | +0.329% | +52.462% | 1.230 | +5.192% | -4.658% | 0.073 | 8.449 | 437/663/2028 | -58.722% |

Drawdowns above are per-ticker strictly non-overlapping trade-close compounding. Pooled portfolio drawdown is undefined; intratrade and daily losses are not measured. No-stop controls have undefined R.

### Independent-event risk-normalized returns

| Policy | Defined R N | Mean R / EV in R | Median R | Win rate in R | Average winning R | Average losing R |
| --- | --- | --- | --- | --- | --- | --- |
| best_atr | 4652 | 0.057 | 0.068 | +54.858% | 0.469 | -0.444 |
| best_fixed | 4652 | 0.058 | 0.042 | +54.450% | 0.381 | -0.327 |
| best_r_multiple | 4652 | 0.059 | 0.064 | +54.729% | 0.476 | -0.444 |
| stop_only | 4652 | 0.083 | 0.034 | +51.720% | 0.768 | -0.652 |
| target_only | 0 | undefined | undefined | undefined | undefined | undefined |
| time_only | 0 | undefined | undefined | undefined | undefined | undefined |
| training_selected | 4652 | 0.059 | 0.066 | +54.794% | 0.473 | -0.444 |
| v1_control | 4652 | 0.070 | 0.044 | +52.279% | 0.727 | -0.650 |

### All fold independent net EV

| Fold | best_atr | best_fixed | best_r_multiple | stop_only | target_only | time_only | training_selected | v1_control |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2021 | +0.658% | +0.731% | +0.636% | +0.598% | +0.740% | +0.827% | +0.636% | +0.508% |
| 2022 | -0.147% | -0.155% | -0.148% | -0.541% | +0.185% | -0.086% | -0.148% | -0.277% |
| 2023 | +1.079% | +1.175% | +1.141% | +1.134% | +1.083% | +1.220% | +1.079% | +0.998% |
| 2024 | +0.946% | +1.346% | +1.026% | +1.076% | +1.052% | +1.447% | +1.026% | +0.745% |
| 2025 | +1.191% | +1.251% | +1.187% | +0.871% | +1.303% | +1.354% | +1.187% | +0.779% |
| 2026 | +0.841% | +0.676% | +0.904% | +0.549% | +0.741% | +1.092% | +0.904% | +0.325% |

### Actual OOS barrier distributions

| Policy | Distance | N | Mean | Median | Q25 | Q75 | Min | Max |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| best_atr | stop_fraction | 4652 | +11.038% | +10.069% | +7.747% | +13.567% | +3.096% | +20.000% |
| best_atr | target_fraction | 4652 | +10.642% | +9.573% | +6.681% | +13.051% | +2.604% | +30.000% |
| best_fixed | stop_fraction | 4652 | +14.156% | +15.000% | +15.000% | +15.000% | +10.000% | +15.000% |
| best_fixed | target_fraction | 4652 | +19.156% | +20.000% | +20.000% | +20.000% | +15.000% | +20.000% |
| best_r_multiple | stop_fraction | 4652 | +11.038% | +10.069% | +7.747% | +13.567% | +3.096% | +20.000% |
| best_r_multiple | target_fraction | 4652 | +12.311% | +10.828% | +6.996% | +15.868% | +3.096% | +30.000% |
| stop_only | stop_fraction | 4652 | +7.000% | +7.000% | +7.000% | +7.000% | +7.000% | +7.000% |
| stop_only | target_fraction | 0 | undefined | undefined | undefined | undefined | undefined | undefined |
| target_only | stop_fraction | 0 | undefined | undefined | undefined | undefined | undefined | undefined |
| target_only | target_fraction | 4652 | +10.000% | +10.000% | +10.000% | +10.000% | +10.000% | +10.000% |
| time_only | stop_fraction | 0 | undefined | undefined | undefined | undefined | undefined | undefined |
| time_only | target_fraction | 0 | undefined | undefined | undefined | undefined | undefined | undefined |
| training_selected | stop_fraction | 4652 | +11.038% | +10.069% | +7.747% | +13.567% | +3.096% | +20.000% |
| training_selected | target_fraction | 4652 | +12.139% | +10.662% | +6.629% | +15.908% | +2.604% | +30.000% |
| v1_control | stop_fraction | 4652 | +7.000% | +7.000% | +7.000% | +7.000% | +7.000% | +7.000% |
| v1_control | target_fraction | 4652 | +10.000% | +10.000% | +10.000% | +10.000% | +10.000% | +10.000% |

### Excursion capture and post-exit recovery

| Policy | Full MFE | Full MAE | Mean capture | Median capture | Defined capture N | Remaining MFE | Stops | Entry+2% after exit | Entry+5% | Entry+10% |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| best_atr | +5.433% | -4.594% | -5.077 | 0.224 | 4627 | +0.366% | 363 | 8/313 (+2.556%) | 3/313 (+0.958%) | 0/313 (+0.000%) |
| best_fixed | +5.433% | -4.594% | -4.493 | 0.200 | 4627 | +0.121% | 174 | 15/152 (+9.868%) | 12/152 (+7.895%) | 2/152 (+1.316%) |
| best_r_multiple | +5.433% | -4.594% | -5.077 | 0.213 | 4627 | +0.285% | 363 | 8/313 (+2.556%) | 3/313 (+0.958%) | 0/313 (+0.000%) |
| stop_only | +5.433% | -4.594% | -4.631 | 0.122 | 4627 | +0.207% | 968 | 156/897 (+17.391%) | 90/897 (+10.033%) | 39/897 (+4.348%) |
| target_only | +5.433% | -4.594% | -4.429 | 0.228 | 4627 | +0.532% | 0 | 0/0 (undefined) | 0/0 (undefined) | 0/0 (undefined) |
| time_only | +5.433% | -4.594% | -4.433 | 0.207 | 4627 | +0.000% | 0 | 0/0 (undefined) | 0/0 (undefined) | 0/0 (undefined) |
| training_selected | +5.433% | -4.594% | -5.077 | 0.219 | 4627 | +0.314% | 363 | 8/313 (+2.556%) | 3/313 (+0.958%) | 0/313 (+0.000%) |
| v1_control | +5.433% | -4.594% | -4.626 | 0.144 | 4627 | +0.700% | 952 | 153/883 (+17.327%) | 88/883 (+9.966%) | 38/883 (+4.304%) |

Signed capture ratios can be very negative when a losing trade has near-zero positive MFE. The negative means are retained; the median is more stable. Neither is used for selection.

### Cross-sectional paired EV difference versus V1

| Policy | Tickers | Positive | Negative | Median | Q25 | Q75 |
| --- | --- | --- | --- | --- | --- | --- |
| best_atr | 74 | 51 | 23 | +0.116% | -0.043% | +0.415% |
| best_fixed | 74 | 59 | 15 | +0.268% | +0.023% | +0.546% |
| best_r_multiple | 74 | 56 | 18 | +0.208% | +0.005% | +0.469% |
| stop_only | 74 | 44 | 28 | +0.025% | -0.049% | +0.123% |
| target_only | 74 | 62 | 12 | +0.262% | +0.065% | +0.550% |
| time_only | 74 | 62 | 12 | +0.284% | +0.042% | +0.666% |
| training_selected | 74 | 53 | 21 | +0.214% | -0.011% | +0.449% |

### Retained ticker heterogeneity: five lowest/highest selected-policy EVs

| Ticker | N | Net EV | Median | Win rate | PF |
| --- | --- | --- | --- | --- | --- |
| AMD | 84 | -0.915% | -1.137% | +44.048% | 0.757 |
| COST | 49 | -0.642% | -0.324% | +44.898% | 0.632 |
| MCD | 52 | -0.584% | -0.297% | +40.385% | 0.659 |
| FDX | 62 | -0.584% | -0.953% | +45.161% | 0.782 |
| MDT | 61 | -0.541% | -0.893% | +45.902% | 0.751 |
| SNDK | 9 | +11.907% | +9.294% | +77.778% | 5.308 |
| PLTR | 55 | +3.286% | +1.585% | +63.636% | 1.988 |
| MU | 72 | +3.265% | +3.397% | +65.278% | 2.309 |
| INTC | 68 | +2.858% | +1.972% | +61.765% | 2.410 |
| AVGO | 69 | +2.614% | +2.057% | +62.319% | 2.379 |

### Training parameter plateaus

| Fold | Family | Winner | Near-best N | Adjacent near-best | Plateau flag |
| --- | --- | --- | --- | --- | --- |
| 2021 | fixed | fixed_s10_t15 | 6 | 3 | True |
| 2021 | atr | atr_s3_t4 | 10 | 4 | True |
| 2021 | r_multiple | r_s3_r1 | 14 | 3 | True |
| 2022 | fixed | fixed_s15_t20 | 6 | 1 | False |
| 2022 | atr | atr_s4_t4 | 8 | 3 | True |
| 2022 | r_multiple | r_s4_r1 | 14 | 3 | True |
| 2023 | fixed | fixed_s15_t20 | 3 | 0 | False |
| 2023 | atr | atr_s4_t2.5 | 5 | 3 | True |
| 2023 | r_multiple | r_s4_r0.75 | 4 | 2 | True |
| 2024 | fixed | fixed_s15_t20 | 3 | 0 | False |
| 2024 | atr | atr_s4_t2.5 | 8 | 3 | True |
| 2024 | r_multiple | r_s4_r0.75 | 11 | 2 | True |
| 2025 | fixed | fixed_s15_t20 | 2 | 0 | False |
| 2025 | atr | atr_s4_t4 | 8 | 3 | True |
| 2025 | r_multiple | r_s4_r1.5 | 13 | 3 | True |
| 2026 | fixed | fixed_s15_t20 | 2 | 0 | False |
| 2026 | atr | atr_s4_t4 | 6 | 3 | True |
| 2026 | r_multiple | r_s4_r1.5 | 11 | 3 | True |

### Training EV/win-rate frontier (controls included)

| Fold | Candidate | Net EV | Win rate | Avg win | Avg loss |
| --- | --- | --- | --- | --- | --- |
| 2021 | atr_s3_t1 | +0.347% | +71.470% | +2.689% | -5.518% |
| 2021 | atr_s3_t1.5 | +0.474% | +63.683% | +3.741% | -5.255% |
| 2021 | atr_s3_t2 | +0.652% | +60.335% | +4.444% | -5.115% |
| 2021 | atr_s3_t2.5 | +0.690% | +58.479% | +4.779% | -5.068% |
| 2021 | atr_s4_t1 | +0.300% | +71.980% | +2.681% | -5.818% |
| 2021 | atr_s4_t1.5 | +0.452% | +64.447% | +3.725% | -5.480% |
| 2021 | atr_s4_t2 | +0.619% | +61.026% | +4.415% | -5.324% |
| 2021 | r_s3_r0.75 | +0.672% | +59.316% | +4.631% | -5.099% |
| 2021 | r_s3_r1 | +0.724% | +57.314% | +4.997% | -5.015% |
| 2021 | r_s4_r0.75 | +0.692% | +58.188% | +4.938% | -5.216% |
| 2022 | atr_s3_t1 | +0.366% | +71.465% | +2.643% | -5.335% |
| 2022 | atr_s4_t1 | +0.356% | +71.999% | +2.638% | -5.512% |
| 2022 | atr_s4_t1.5 | +0.507% | +64.183% | +3.661% | -5.144% |
| 2022 | atr_s4_t2 | +0.655% | +60.753% | +4.314% | -5.008% |
| 2022 | atr_s4_t2.5 | +0.702% | +58.954% | +4.632% | -4.944% |
| 2022 | r_s3_r0.75 | +0.670% | +58.982% | +4.525% | -4.874% |
| 2022 | r_s4_r0.75 | +0.738% | +58.083% | +4.814% | -4.910% |
| 2022 | r_s4_r1 | +0.747% | +57.324% | +4.938% | -4.883% |
| 2023 | atr_s4_t1 | +0.324% | +71.080% | +2.795% | -5.750% |
| 2023 | atr_s4_t1.5 | +0.472% | +63.329% | +3.890% | -5.431% |
| 2023 | atr_s4_t2 | +0.588% | +59.655% | +4.546% | -5.265% |
| 2023 | atr_s4_t2.5 | +0.628% | +57.841% | +4.866% | -5.186% |
| 2023 | r_s3_r0.75 | +0.592% | +57.908% | +4.768% | -5.154% |
| 2024 | atr_s4_t1 | +0.393% | +71.340% | +2.762% | -5.505% |
| 2024 | atr_s4_t1.5 | +0.546% | +63.577% | +3.835% | -5.195% |
| 2024 | atr_s4_t2 | +0.665% | +59.869% | +4.483% | -5.030% |
| 2024 | atr_s4_t2.5 | +0.712% | +58.111% | +4.798% | -4.956% |
| 2024 | r_s3_r0.75 | +0.682% | +58.266% | +4.694% | -4.921% |
| 2024 | r_s4_r0.75 | +0.717% | +57.165% | +4.951% | -4.933% |
| 2025 | atr_s4_t1 | +0.369% | +70.944% | +2.722% | -5.377% |
| 2025 | atr_s4_t1.5 | +0.526% | +63.204% | +3.785% | -5.071% |
| 2025 | atr_s4_t2 | +0.672% | +59.629% | +4.453% | -4.912% |
| 2025 | atr_s4_t2.5 | +0.740% | +57.943% | +4.793% | -4.843% |
| 2025 | r_s3_r0.75 | +0.694% | +58.111% | +4.676% | -4.831% |
| 2025 | r_s4_r0.75 | +0.755% | +57.032% | +4.955% | -4.821% |
| 2025 | time_only | +0.778% | +56.459% | +5.100% | -4.826% |
| 2026 | atr_s4_t1 | +0.416% | +71.169% | +2.750% | -5.347% |
| 2026 | atr_s4_t1.5 | +0.559% | +63.235% | +3.818% | -5.047% |
| 2026 | atr_s4_t2 | +0.720% | +59.701% | +4.503% | -4.886% |
| 2026 | atr_s4_t2.5 | +0.781% | +57.926% | +4.847% | -4.818% |
| 2026 | r_s3_r0.75 | +0.726% | +58.073% | +4.730% | -4.821% |
| 2026 | r_s4_r0.75 | +0.805% | +57.061% | +5.021% | -4.797% |
| 2026 | target_only | +0.801% | +57.090% | +4.954% | -4.724% |
| 2026 | time_only | +0.846% | +56.533% | +5.147% | -4.748% |

### Scientific interpretation and limitations

The tables compare training-selected policies; no candidate was selected on its OOS score. Higher EV may buy greater tail loss or deeper ticker drawdown. Target-only/time-only controls must remain visible when interpreting barrier value. A favorable comparison on these consumed dates is exploratory historical evidence. There is no prospective confirmation.

Current-constituent survivorship selection, 21 retained data-quality exclusions, revised adjusted prices, daily OHLC ambiguity, overlapping outcomes, unequal histories and uncalibrated execution/capital assumptions remain. Date-block intervals do not resolve multiple testing or all ticker dependence. MFE includes high/low information whose intraday ordering is unknown; recovery highs after stop exits are descriptive and may not be executable.

Next hypothesis (not implemented): test whether signal-time price structure can control tail loss without surrendering rebound capture. Keep it separate as EXP-005; first review the recorded trade-offs and preserve a policy before genuine prospective comparison.
<!-- EXP004_RESULTS_END -->
