# Adaptive exits and expected value

This unrun preparation was superseded, at explicit user request before results,
by [EXP-004 revision 2](EXP004_ADAPTIVE_EXITS.md). The original configuration
remains preserved; the current catalogue is `config/exp004.json`.

**Status: preparation only. No new exit setting has been selected or tested.**

V1 stays frozen at +10% target, -7% stop and 10 observed bars. EXP-001/002
holdouts are consumed, so their results cannot identify a “best” exit without
turning reported holdouts into tuning data.

## Candidate method

The prototype in `src/exit_research.py` converts signal-time ATR(14) into
stock-specific target and stop distances. ATR uses completed bars through signal
day; the levels are anchored to the next observed open. The caller supplies
multipliers. This code does not choose them, alter V1, or run a backtest.

## EXP-004 protocol (registered, not run)

- Keep V1 signals, next-observed-open entry, 10-bar maximum, costs, and
  conservative same-bar rule fixed. The comparator remains +10% / -7%.
- Use signal-session ATR(14). Candidate stop distances are 1, 1.5, 2, or 2.5
  ATR; candidate reward-to-risk ratios are 1, 1.5, or 2, with target distance
  equal to stop distance times that ratio. No other candidates.
- Fit one shared multiplier pair across all eligible names using only the
  chronological `research` split. Pick the pair with highest pooled **net EV**;
  exact ties prefer the smaller stop multiple, then smaller reward-to-risk ratio.
  Retain every ticker passing unchanged data validation; no performance-based
  exclusions. Do not use validation/test split outcomes to select a pair.
- Report research-fit results as in-sample only. The historical validation and
  test periods have already been inspected and cannot validate EXP-004. Freeze
  the selected pair before any use on prospective records; compare it with V1
  only at EXP-003's registered review date and coverage gate, after separate
  authorization. If calibration data are inadequate, report no selected pair.
- Report per-fold/per-ticker net EV, baseline V1 results, trade count, median,
  win/loss probabilities and sizes, break-even win rate, exit mix, MFE/MAE, and
  block-aware uncertainty. The mean net return is EV; win rate alone is not.
  No interim peeking, candidate changes, or repeat review dates.

This protocol does not claim an improved rule. The candidate grid is fixed before
any new exit results are calculated.

ATR scaling adapts to recent range, not company fundamentals or future news. It
can widen stops on volatile stocks and narrow them on calm stocks, but that alone
does not improve EV. Historical adjusted data, costs, daily-bar execution order,
small samples and survivor bias remain limitations. The selected policy may still
fail prospectively.
