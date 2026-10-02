# EXP-004 - Adaptive Exit Policy Research

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
