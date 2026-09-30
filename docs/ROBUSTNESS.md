# EXP-002 robustness infrastructure

EXP-002 asks whether the unchanged DipSignal V1 behaves similarly across more
stocks and repeated historical periods. Its protocol and universe were pushed in
`ff6a99d` before new stock history acquisition or outcome evaluation. See the
immutable protocol section in [EXPERIMENTS.md](EXPERIMENTS.md). EXP-001 remains a
mixed first evaluation; its inspected test period cannot be reused as fresh evidence.

## Universe and provenance

`config/exp002.json` freezes the September 29, 2026 US equity holdings of
[iShares OEF](https://www.ishares.com/us/products/239723/ishares-sp-100-etf), retrieved
September 30. All 101 source symbols are stored as compact configuration, together
with the source CSV hash. Exclude AAPL, AMZN, MSFT, NVDA, GOOGL and GOOG (same
already-inspected issuer), leaving 95 requested stocks. No size/performance ranking
is performed and failed downloads are not replaced. SPY is benchmark-only.

This is a **current-constituent / static-universe robustness test**, with survivor
selection and current size/liquidity selection. It is not historical S&P 100
membership, a historical liquidity screen, or a point-in-time equity universe.
It offers fresher cross-sectional evidence but not a new temporal holdout. Market
regimes and the research concept overlap previously inspected history.

`src/universe.py` exposes:

- `static_universe`: canonical sorted unique symbols; duplicates and invalid names raise.
- `select_universe`: deterministic exclusions without ranking or replacement.
- `validate_membership`: canonical disjoint `[start_date, end_date)` intervals
  per ticker; null end means open-ended. Re-entry and adjacent intervals are allowed.
- `membership_mask`: apply static or interval eligibility to signal-date identities.

An interval table does not certify point-in-time provenance. Genuine membership
data must identify its source, availability dates, revisions and historical identities.
Ticker reuse, delistings and corporate-action histories require separate data work.
Never fabricate intervals from today's constituents and label them historical.

Eligibility gates observations after full-history V1 generation. Price rows remain
available for features and outcome paths; no price filling or history compression
occurs. Admission does not create a new V1 event. Membership is measured at the
signal date; accepted paths may continue past a later removal. Future removals are
not used to retrospectively select events. This convention would need review for
an investable mandated-index portfolio, which EXP-002 does not simulate.

## Frozen signals and expanding folds

Feature and signal source hashes guard the unchanged EXP-001 implementation.
The explicit runner settings remain 252 prior positions, 126 valid observations,
20th-percentile lower tail, three of four components, full readiness and existing
rising-edge semantics. Every 1/3/5/10/20-bar horizon is retained. The barrier is
+10% / -7% / 10 bars, conservative same-bar resolution, 1 bp commission and 5 bp
slippage each side. See [BACKTESTING.md](BACKTESTING.md) for formulas and gap fills.

`annual_folds` uses sorted unique SPY dates. After four calendar years of history,
the next January 1 begins annual OOS windows. With the frozen data range this is
2021–2026; 2026 is partial. Each fold shares the same history origin and has a
strictly earlier history end. Overlapping, unordered or nonexpanding folds raise.
Partial-year flags compare observed endpoints to the final weekday of the year;
this is not an exchange-calendar completeness guarantee.

V1 has no fitted model. Full-history causal features/signals can be calculated
once: deterministic tests compare this against prefix recalculation. At each fold,
the evaluator truncates stock and benchmark prices to the fold end **before**
calling the existing outcome engine. Only OOS eligible signal dates are selected.
Thresholds update with newly available completed bars within OOS, without refitting
parameters or accessing later data.

Incomplete full horizons/max-hold paths are audited as `incomplete_window` or
`no_next_bar` at fold ends, including early barrier hits whose full window is
unobservable. No cross-fold prices, forced liquidation or partial-horizon substitute
is used. Non-overlap starts fresh at each fold because accepted earlier positions
cannot cross its boundary. Future supervised model fitting would require explicit
label purging and an embargo; no such fitting occurs here.

Forward outcomes now use per-ticker vectorized endpoint/extrema calculations to
make larger unconditional samples practical. This is a computational change only:
the complete cached EXP-001 report matched exactly after the change, and all original
execution/censoring tests pass. One eligible ledger per fold supplies event and
non-condition subsets, preserving the same baseline calculation.

## Aggregation, uncertainty and concentration

Summaries retain all five horizons, both trade modes, all folds, all requested
tickers and predeclared regimes. Pooled event/trade means weight observations;
equal-ticker distributions separately expose unequal activity. Undefined outcome
means and zero-event stocks are retained in denominator accounting. A stock with
no ready OOS observation is explicitly excluded for insufficient history; shorter
histories join later folds only when causally ready.

Ticker distributions include positive/negative/zero/undefined counts, equal-ticker
mean, median, quartiles, IQR and range. Event distributions include paired SPY excess;
barrier distributions use net non-overlapping expectancy. Frequency tables report
observed/member/ready/condition/event counts, condition fractions using both ready
and eligible denominators, and events per 252 ready observations. Missing ticker-fold
coverage is recorded as zero exposure, never as fabricated price rows.

Contributions are sums of equal-notional return fractions, **not portfolio returns**.
Report every ticker's sum/count/mean, total positive and negative ticker sums, top
five positive contribution share, and top five absolute contribution share. Signed
net totals can approach zero, so they are not used as percentage denominators.
No ticker is removed based on these diagnostics. Sharpe, Sortino, pooled compounded
returns and portfolio drawdowns remain undefined without allocated equity accounting.

The existing seeded circular bootstrap keeps same-date stock rows together and
resamples blocks of 20 observed dates, with 2,000 draws and minimum 40 clusters.
Intervals describe means, not significance of differences against stock/SPY controls.
They approximate dependence; persistent cross-ticker correlation, nonstationarity,
sparse subgroups and blocks crossing pooled fold gaps remain limitations.

Descriptive criteria were registered before results: strict-majority favorable
10-bar fold comparisons and positive ticker paired-excess means for directional
breadth; separate majority-positive fold/ticker net expectancy for barrier stability.
Top-five positive share over 50% flags concentration. Passing these diagnostics
does not establish significance, profitability, or out-of-universe generalization.

## Causal market context

Only SPY supplies regimes: completed signal-date close above/equal to its trailing
200-observation simple mean versus below. Require a full window, join exact dates,
and preserve unknown values. No optimized threshold, future label, forward fill,
or complex classifier is introduced. Report pooled and per-fold outcomes and
trades in each regime, plus existing three/four-component 10-bar subgroups.

## Reproduction and artifacts

```powershell
# Acquisition only; uses existing get_history API, never refreshes cached symbols.
.\.venv\Scripts\python.exe -W error -m scripts.evaluate_exp002 --download --prepare-only
# Default is offline; missing histories are explicitly excluded, corrupt caches raise.
.\.venv\Scripts\python.exe -W error -m scripts.evaluate_exp002
# Replay to another ignored directory and compare metadata artifact hashes.
.\.venv\Scripts\python.exe -W error -m scripts.evaluate_exp002 --output-dir results/exp_002_replay
.\.venv\Scripts\python.exe -m pytest -q -W error --tb=short
```

Acquisition attempts each missing symbol at most twice. Data failures are recorded
in an ignored configuration-bound cache audit so offline replay preserves their
reasons. Benchmark failure or a corrupt existing snapshot raises. Preserve caches
and `data/market/exp002-acquisition.json` together before refreshing any history.
Provider-adjusted prices remain revised historical vintages, not point-in-time data.

Ignored `results/exp_002/` contains Parquet event/control/trade/observation ledgers;
CSV fold, pooled, ticker, regime, component, status, frequency, distribution and
contribution summaries; `exclusions.csv`; and `metadata.json`. Metadata records
requested/usable names, exact folds, fixed configuration, source provenance, input
and execution-source hashes, environment, revision/dirty state, and output hashes.
There is no run-time timestamp in deterministic output; retrieval timestamps belong
to input provenance. A new code commit changes provenance even if metrics agree.

## Future genuinely unseen temporal holdout policy

After EXP-002 all inspected names/dates are consumed. A later authorized paper-signal
archive should append after-close signals with observation/publication timestamps,
data vintage, universe eligibility, code/config hashes and intended next-open
execution before outcomes become known. Preserve corrections as new versions.
Predeclare its evaluation dates, sample targets, costs and interpretation before
collecting outcomes. Never replace an unfavorable frozen specification mid-holdout
and still call the resulting sample untouched. Do not fabricate or wait for future
outcomes in this task. Archive/scanner implementation and further models remain
separate milestones requiring review of robustness results.
