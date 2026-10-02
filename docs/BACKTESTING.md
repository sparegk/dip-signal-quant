# DipSignal V1 evaluation foundation

This module measures **post-signal outcomes**. It does not modify features, choose
events, optimize parameters, or establish profitability. Signal and outcome tables
are separate. Inputs are the canonical OHLCV plus boolean `dip_event_v1`,
`dip_condition_v1`, `dip_ready_v1`, and integer `dip_component_count` from the
existing signal engine. Bad schemas, prices, identities, ordering, and configuration
raise. No filling or network calls occur.

## Timing and fixed horizons

An event uses information through the close of session t. Entry is the next
observed **same-ticker open**, never t's close. Missing exchange sessions are not
reconstructed: this is an observed-bar convention, not a calendar-completeness audit.

`compute_forward_outcomes` returns one separate row per selected observation and
horizon (defaults 1, 3, 5, 10, 20). The entry bar counts as bar 1. Thus horizon 1
is entry-day open to entry-day close; horizon 5 ends at the fifth bar's close,
including entry day. With entry price E and endpoint bar n:

- `forward_return = close[n] / E - 1` (gross, no costs).
- `mfe = max(high[entry:n]) / E - 1`.
- `mae = min(low[entry:n]) / E - 1` (negative or zero, not a positive loss magnitude).

These extrema include both endpoints and are outcome measurements only. Missing
full windows never produce shorter-horizon substitutes. Every requested observation
is audited with `status`: `completed`, `no_next_bar`, `incomplete_window`, or
`split_boundary`. Uncompleted rows have NaN outcomes and NaT execution endpoints.

## Illustrative barrier model

`simulate_barrier_trades` defaults to target +10%, stop -7%, maximum holding 10
observed bars, conservative ambiguity policy, independent events, and zero costs.
These parameters are illustrative, not optimized or claimed optimal.
Target must be a finite positive fraction; stop must be strictly between 0 and 1;
holding bars must be a positive integer. Costs must be finite fractions in [0, 1).
Boolean configuration values and numerically unrepresentable barriers raise.

Barriers are fixed relative to the observed un-slipped entry open E. Starting on
the entry bar, inspect each bar in chronological order:

1. Open at/below stop: exit at that observed open.
2. Open at/above target: exit at that observed open.
3. Otherwise inspect high/low: a touch exits at the barrier reference price.
4. If both barriers are touched, `conservative` chooses stop; optional `optimistic`
   chooses target. Record `ambiguous_bar`. No intraday sequence is inferred.
5. If neither barrier is touched on the last holding bar, exit at its close.

Open hits precede intraday tests even when that day's later range touches both
barriers. An entry gap is not itself a stop relative to yesterday's close: barriers
are established only from actual entry. Inclusive touch comparisons allow only
eight floating-point epsilons of relative roundoff, not a tick-size buffer.
Daily stop fills remain approximations: a stop price is not a guaranteed execution
price ([SEC order guidance](https://www.investor.gov/introduction-investing/investing-basics/how-stock-markets-work/types-orders)).

Trade records contain entry/exit dates and reference/fill prices, reason
(`take_profit`, `stop_loss`, `time_exit`), fill type (`open`, `barrier`, `close`),
holding bars, gross/net return, ambiguity, and excursion scope.

Trade `mfe`/`mae` are **bar envelopes, not exact pre-exit excursions**: full highs/lows
through an intraday barrier/close exit bar, potentially including movement after
an intraday fill. `excursion_scope=through_exit_bar` makes this explicit. For an
open exit, exclude that day's later high/low and use only the open plus earlier
bars (`through_exit_open`). Exact intraday trade MFE/MAE require intraday data.

## Costs and overlap

For per-side slippage s and commission c:

```text
entry_fill = E * (1+s)
exit_fill = X * (1-s)
gross_return = X/E - 1
net_return = X*(1-s)*(1-c) / (E*(1+s)*(1+c)) - 1
```

Commission is charged on each slipped transaction notional; denominator includes
entry costs. Cost parameters do not move barriers or select exits. Rates are
fractions, not percentage points. Defaults zero permit raw comparisons. A separate
illustrative liquid-equity cost scenario is 1 bp commission and 5 bp slippage per
side (`0.0001`, `0.0005`); this is a research assumption, not a calibrated guarantee.
Slippage is an adverse market-fill overlay even on target exits, not an exact
resting limit-order/auction model. No spread, queue, partial-fill, impact, or capacity
model is implemented beyond this overlay.

`mode=independent` evaluates every event, including overlapping paths.
`mode=non_overlapping` allows one active trade per ticker; a proposed entry on or
before that ticker's last exit date is audited as `overlap`. No same-open capital
recycling is assumed. An event computed on the prior trade's exit-day close may
enter on the next open. Other tickers are independent. This is not portfolio
allocation; simultaneous positions across stocks require capital not modelled here.

## Chronological splits and censoring

`assign_research_splits` copies the input and assigns research/validation/test by
common session dates across the universe. Default boundaries are unique-date
indices floor(0.6*N) and floor(0.8*N), independent of stock counts, signal frequency,
or outcomes. Boundary dates are included in the later split. Explicit
`validation_start` and `test_start` freeze partitions for repeat work; appending
history and recomputing fraction cuts would change them. Metadata records cuts.

Create causal features/signals on full supplied history first so later splits
retain legitimately available trailing history. Assign outcomes by signal date,
but require the entire forward horizon to remain inside that split. Barrier
simulations require the **full configured maximum window** before inspecting
barrier hits. This drops some otherwise observable early exits near boundaries,
but avoids retaining only early winners/losers with unavailable longer outcomes.
No forced boundary/end-of-sample liquidation occurs. Exclusions remain in the audit
table and counts must be reported. Without `split`, APIs explicitly label rows
`all`; the research experiment must use splits.

The final test partition is designated historical out-of-sample for this fixed
specification; reporting it consumes the holdout. It must not become a tuning set.
It is not prospective unseen evidence or a point-in-time dataset.

## Optional barriers for separately registered exit research

The EXP-004 extension allows `stop_loss=None` or `take_profit=None` to disable
that barrier. `stop_loss_column` / `take_profit_column` name causal fractions on
the signal row, frozen through the trade and anchored to its next open. Event
fractions must be valid; missing values raise. This is the same fill/cost engine,
not a second simulator. Default V1 ledgers are unchanged. See
[EXP004_ADAPTIVE_EXITS.md](EXP004_ADAPTIVE_EXITS.md) for registration and diagnostics.

## Baselines

The same forward-outcome function supports `selection=eligible` (all ready rows,
unconditional on signal) and `selection=non_signal` (ready, condition=false rows).
The latter excludes persistent condition days, not merely event entry days. Apply
identical horizons and boundary censoring. Both contain dependent overlapping windows.

Supply SPY explicitly as `benchmark`. Its return uses SPY open on the stock entry
date and SPY close on the stock endpoint date. Either absent endpoint makes benchmark
and excess return NaN, without filling or invalidating the stock outcome. Interior
benchmark dates are not needed for this endpoint return. `excess_return` is stock
minus matched benchmark return, not a compounded relative wealth ratio. Compare
stock/benchmark means on paired rows; disclose paired counts. No fixed-drawdown
baseline or optimized technical-strategy baseline is introduced.

## Metrics and uncertainty

`summarize_returns` reports valid/missing counts, mean, median, sample standard
deviation (ddof=1), win rate (return > 0), expectancy (mean including zero returns),
and profit factor (sum positive returns / absolute sum negative returns; undefined
with no losses). Equal-return-notional weighting is implicit, not dollar P&L.

Mean uncertainty uses a seeded circular moving-block bootstrap. For event reports,
first group all stocks sharing a signal date together, then sample contiguous
blocks of 20 distinct **observed event dates**, wrapping around the sample. Draw
enough blocks to recreate the number of date clusters; keep entire clusters so
same-day cross-stock dependence is retained. Weight the resulting mean by rows,
not equally by date. Use 2,000 resamples, seed 42, bootstrap standard deviation as
standard error, and 2.5/97.5 percentile endpoints as a 95% interval. Require at
least 40 date clusters for the default block size; otherwise SE/CI stay undefined.

Blocks are a transparent dependence approximation, not a proof of calibrated
coverage, stationarity, independence, or statistical significance. Twenty event
dates are not necessarily twenty sessions. Sparse subgroups may have no interval.
Controls use the same rule on their selected observation dates. The low-level API
allows other block sizes and an explicit IID case (one row per cluster, size 1),
but EXP-001 does not select a block size based on its results.

`summarize_outcomes` groups by split/horizon by default, with configurable grouping
such as component count or ticker. It includes excluded counts, mean MFE/MAE,
paired benchmark counts/means, and mean stock-minus-benchmark return. Pooling stocks
uses one weight per observation; event and unconditional samples can have different
ticker/date composition, so their mean difference is descriptive, not causal alpha.

`trade_metrics` reports candidate/completed/excluded counts, gross/net mean return,
net median/std/win rate/expectancy/profit factor, average bar-envelope MFE/MAE,
holding bars, and TP/SL/time-exit rates. Missing/invalid completed metrics raise.
Pooled independent or per-ticker non-overlap streams are **not** an allocated
portfolio, so cumulative return, Sharpe, Sortino, and drawdown are not reported
as pooled performance. In a single sorted non-overlapping ticker stream,
`sequential=True` reports hypothetical full-reinvestment cumulative return and
trade-close maximum drawdown, including initial wealth 1. Idle cash earns zero;
intratrade mark-to-market losses are absent. This is not daily portfolio drawdown.

`risk_adjusted_metrics` is available only for caller-supplied regular-period
non-overlapping capital returns. Sharpe = mean(r-rf)/sample_std(r-rf)*sqrt(K).
Sortino = mean(r-target)/sqrt(mean(min(r-target,0)^2))*sqrt(K), using **all periods**
in downside deviation. K defaults to 252; rf and target are per-period fractions,
default zero. Insufficient samples or zero denominators produce NaN, not infinity.
No regular portfolio-equity series is constructed here; EXP-001 correctly leaves
these ratios undefined for variable-holding, overlapping trade/event samples.

## Reproduction and scope

```powershell
.\.venv\Scripts\python.exe -W error -m scripts.evaluate_v1
.\.venv\Scripts\python.exe -m pytest -q -W error --tb=short
```

Use the existing project environment (or activate it before using `python`); a
global interpreter may lack the pinned dependencies. The recovered EXP-001 run
reproduced all documented table values; see its verification note for provenance.

The runner requires existing AAPL/MSFT/NVDA/AMZN/GOOGL/SPY snapshots and fails if
any are missing. It patches provider downloading to fail, prints JSON to stdout,
and writes no artifacts. It records snapshot SHA-256 hashes, provider provenance,
environment, code revision/dirty state, signal/exit settings, split dates, all
five forward horizons, component-count subgroups at 10 bars, both trade modes,
and per-ticker sequential summaries. No parameter search exists. See EXP-001 in
[EXPERIMENTS.md](EXPERIMENTS.md) for the fixed protocol and observed results.

pandas handles identity/date alignment and grouping; NumPy handles numerical
summaries and bounded-batch bootstrap sampling. Per-event/path loops keep first-hit
execution semantics explicit for daily research. No new dependency or unnecessary
pandas/Polars conversion is introduced. Large-universe throughput is not benchmarked.

Limitations include a survivor-selected five-stock universe, revised adjusted
prices rather than point-in-time executions, no delisting/corporate-action cash
ledger, daily intrabar ambiguity, hypothetical fill/liquidity/cost assumptions,
overlapping dependent event windows, limited effective sample size, boundary
censoring, and no portfolio allocation. Negative results must be retained.
