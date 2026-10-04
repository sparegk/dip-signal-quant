# EXP-005 — prospective validation

Registered before collection. Historical tuning is paused. No historical result
is evidence for this experiment, and V1 is unchanged.

## Frozen comparison

The 95 ordered requested names in frozen `config/exp003.json` are the universe;
SPY is the benchmark only. First eligible signal session: **2026-10-05**.
This is a static current-constituent universe with survivorship limitations.
Keep unavailable names and failures; never replace them.

Use frozen V1 features and 252/126/0.20/3-component rising-edge signals.
After a completed XNYS session, retrieve its bars and publish immutable decisions
between 00:15 America/New_York the following calendar day and the next scheduled
open. Record actual UTC timestamps; no caller-supplied historical clock.
Prospective mode refuses any session other than the currently eligible session.
Explicit historical replay is permanently excluded. Publication after the open,
stale inputs, dirty code or uncertain timing cannot enter the holdout.

Every original prospective event receives the same next-observed stock open:

1. Historical V1 exit control: 7% stop, 10% target, ten-bar timeout.
2. Ten-bar hold: no stop or target, tenth observed bar close.

Reuse the existing gap-aware, conservative stop-first execution engine. Costs:
1 bp commission and 5 bp slippage **per side**. Independent same-entry events
are primary; they are dependent observations, not portfolio returns.
No adaptive selection, new signals, filters or universe changes are permitted.

## Decision context and volatility

Retain original source snapshots, thresholds, component flags, readiness,
condition, event, price/volume/ATR and causal SPY regime context. Outcomes are
separate, never additions to the original decision.

For each ticker, compare signal-day ATR14/close with the 1/3 and 2/3 quantiles
of the **previous 252 observed bars**, requiring 126 valid prior ratios.
Linear quantiles; current observation excluded. Low means <= lower boundary,
middle means > lower and <= upper, high means > upper. Missing/insufficient
history is `unavailable`. Save the ratio and both boundaries before entry.
These groups describe context; they never select trades.

## Outcomes and revisions

Preserve 1/3/5/10/20-bar returns, MFE/MAE and matched-SPY returns from a
separately retained outcome vintage. Attach only after the relevant bars have
closed and were retrieved. Pair barrier/hold statistics only when the full
ten-bar window is available, even if a barrier was hit earlier. Missing entry,
benchmark or horizon stays pending/unavailable; never fill missing prices.
Record observed entry/exit sessions and execution assumptions explicitly.

Outcome snapshots use one internally consistent adjusted-price vintage. Report
changes from decision-vintage prices; adjusted revisions are not point-in-time
prices. Keep originals and append explicit correction versions with parent and
reason; never replace either decisions or outcomes. Interrupted publication is
not evidence. Local hashes detect alteration relative to retained hashes; they
are not tamper-proof or independent timestamp witnesses.

## Review policy

Operational coverage and maturity counts may be inspected daily. **No daily
performance dashboard or tuning on accumulating returns.** First outcome review
is 2027-04-01, then 2027-10-01, preserving EXP-003's gates: at least 100 scheduled
sessions and at least 80% complete timely original runs across all 95 names.
If a gate fails, show the failure and defer; do not drop failing symbols.
Reports at registered dates identify cumulative 50/100/250/500-completed-event
milestones crossed since the last review. Crossing a count does not authorize
an earlier review. Do not stop early, restart losses or selectively extend.
Further review dates require a new advance registration.

Primary measures: ten-bar gross mean/median and matched-SPY excess, net EV and
profit factor, paired hold-minus-control EV. Secondary: win rate, mean win/loss,
MFE/MAE, fifth percentile, worst loss, per-ticker drawdown, rebound timing and
calendar/ticker/volatility breakdowns. Show event dependence and uncertainty;
do not interpret naive independent-event intervals as definitive.

Strong support requires positive EV, excess and median, breadth across at least
two calendar quarters and a majority of eligible tickers, with no ticker
providing over half of positive equal-notional contributions. An exit improvement
additionally needs positive paired EV difference without worse fifth-percentile
return or mean loss than control. Mixed support includes insufficient counts,
positive EV with weak excess, concentrated results or poorer downside. Nonpositive
EV and excess with poor downside provide no support. These descriptive categories
do not establish significance or guaranteed profitability. Fewer than 100 complete
events remain insufficient for a strong conclusion regardless of point estimates.

The archive remains cumulative and unsuccessful events stay included. There are
currently no EXP-005 prospective outcomes. EXP-004 and repeated-support findings
remain historical hypotheses only.
