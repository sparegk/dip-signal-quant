# Experiment registry

No strategy experiments have been run. Do not infer performance from data-layer
tests. Add an entry for every significant experiment, including negative results.
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
