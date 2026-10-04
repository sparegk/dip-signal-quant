# EXP-005 proposal — prospective controls and volatility context

**Proposal only. Not registered, implemented as a strategy, or evaluated.**
Choose at most these two questions. No new signal or parameter optimization.

## Question 1: Does ten-bar holding improve the profit/risk trade-off?

- Signals: unchanged V1, 252/126/0.20/three components, objective frozen EXP-003
  requested universe and genuine original prospective events only.
- Entry: next observed open after a completed signal session, same entry for both
  policies. Observe actual unavailable/delisted/missing inputs without substitution.
- Comparator: frozen V1 7% stop / 10% target / ten-bar timeout versus no barriers,
  exit at the tenth observed bar close. Retain conservative V1 gaps/ambiguity and
  1 bp commission + 5 bp slippage per side.
- Mechanism: let recovery unfold instead of truncating it at a barrier. No-stop
  trades can suffer large losses up to invested capital; a risk improvement is not assumed.
- Primary: paired net EV difference. Also paired matched-SPY excess, median,
  losses, fifth percentile, per-ticker drawdown, fold/ticker breadth and missing
  outcomes. Independent same-entry events are primary; no-overlap is secondary.
- Failure: no positive paired net EV improvement, or materially worse downside
  relative to V1. Profit alone cannot establish superiority. Before registration,
  specify an acceptable risk deterioration based on a chosen capital/risk budget;
it is currently unresolved, so there is no executable acceptance rule yet.

## Question 2: Does volatility describe prospective dip quality?

- Same V1 events and entries; **no filter** and no signal selection.
- Information: signal-date ATR14 / close, saved before the next-open opportunity.
- Groups: <=2%, >2% through 4%, >4%; missing values remain a separate group. These
  reuse the existing recorded diagnostic boundaries without tuning them.
- Mechanism: volatility changes rebound scale and risk; high return alone is not
  enough. Compare ten-bar gross/paired SPY excess, net V1 EV and MAE by group.
- Failure: historical ordering does not repeat, excess remains weak, or higher EV
  is accompanied by risk that defeats a subsequently registered risk budget.
  Treat insufficient subgroup counts as inconclusive, never as success.

## Prospective validation and acceptance policy

Register exact code, configuration, source hashes, review date and minimum count
**before** collection under this proposal. Do not relabel older archive records as
new holdout. Keep EXP-003's review dates/gates; earliest review is 2027-04-01,
deferring to 2027-10-01 when its registered maturity/count gate is unmet. This
proposal cannot authorize interim outcome inspection or override those gates.

The gate requires complete timely runs across all requested names. Persistent
ingestion failures could prevent it from being met. Review collection coverage
and data-quality remediation separately; do not silently drop unavailable tickers
or relax the gate after looking at returns.

Attach future outcomes separately without editing decisions. Preserve losing,
unavailable and censored events. Report paired date-block uncertainty and all
predeclared groups; prospective event dependence and multiplicity remain limits.
An interesting result needs improved net EV and excess, acceptable downside,
reasonable counts and improvement across time/stocks. No arbitrary 60% win-rate
or 5% return target applies. Risk budget and exact future count gates must be
resolved before registration; this document is intentionally a proposal.

EXP-004's fold-varying training winner is **not** a single frozen prospective
policy. A future adaptive comparison needs its own advance policy definition;
do not choose it using accumulating prospective outcomes.
