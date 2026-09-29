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
- Results: pending the first frozen-protocol cached-data run; no outcomes inspected yet.
