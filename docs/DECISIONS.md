# Decisions

Lightweight architecture decision records. Append new entries when decisions
change; preserve their context rather than rewriting the research history.

## ADR-001 — Daily timeframe for V1

Date: 2026-09-30. Status: Accepted.

Decision: Begin with daily equity data before considering intraday signals.

Reason: Simpler research environment, longer clean history, faster iteration,
and lower noise. Daily observations still require careful signal availability
and execution timing; a completed bar cannot inform an earlier fill.

## ADR-002 — Parquet as persistent market-data format

Date: 2026-09-30. Status: Accepted.

Decision: Store cleaned history in one Parquet file per normalized ticker under
`data/market/`; exclude generated data from Git.

Reason: Columnar storage, compression, and compatibility with pandas, Polars,
PyArrow, and future DuckDB queries. Symbol files allow independent refreshes.

## ADR-003 — Research-first architecture

Date: 2026-09-30. Status: Accepted.

Decision: Validate signal quality before building UI, broker integrations, or
live execution.

Reason: Reproducible evidence should drive system complexity. Infrastructure
alone is not evidence of predictive power or profitability.

## ADR-004 — Hybrid pandas / Polars / NumPy stack

Date: 2026-09-30. Status: Accepted.

Decision: Use the right tool for each workload rather than forcing all processing
through one dataframe library.

Reason: pandas naturally receives yfinance data and supports future VectorBT
research. NumPy provides array validation and numerical operations. Polars is
reserved for workloads such as lazy Parquet scans when they offer a real benefit.
Avoid repeated conversions; use PyArrow for Parquet persistence and metadata.

## ADR-005 — Explicit adjustment and validation contract

Date: 2026-09-30. Status: Accepted.

Decision: Request daily yfinance auto-adjusted OHLC and retain provider-reported
volume. Reject missing or malformed bars, remove only identical duplicates, and
exclude today's potentially incomplete US session. Preserve exchange session dates.

Reason: Avoid implicit library defaults, hidden filling, and accidental inclusion
of partial daily bars. Current adjusted history is not point-in-time data; later
research must account for corporate-action revisions and signal availability.

## ADR-006 — Explicit, atomic per-symbol cache snapshots

Date: 2026-09-30. Status: Accepted.

Decision: Existing snapshots load offline until explicitly refreshed. Save request
provenance in Parquet metadata and replace an entire symbol history atomically.
Explicit date requests outside known coverage raise instead of returning a silently
truncated history. Download symbols sequentially and concatenate cleaned data once.

Reason: Preserve failed-refresh recovery and keep adjustment vintages consistent.
Snapshots are convenient local caches, not immutable experiment archives; users
must preserve experiment inputs before refreshing. Sequential requests bound traffic
and avoid cross-symbol date padding; optimize concurrency only with evidence.

## ADR-007 — After-close, per-ticker feature availability

Date: 2026-09-30. Status: Accepted.

Decision: Calculate features independently by ticker using full trailing windows
of observed bars. Features at t include t's completed bar and are available after
the close; later execution generally occurs at t+1 or later. Preserve all warm-up
NaNs. Reuse data validation without changing the market-data API.

Reason: Explicit timing and ticker boundaries prevent accidental future-data use
or cross-symbol windows. Adding/changing future observations must leave historical
features unchanged. Observed-bar causality does not remove data-vintage bias or
guarantee complete exchange calendars.

## ADR-008 — Explicit indicator initialization and undefined values

Date: 2026-09-30. Status: Accepted.

Decision: Use arithmetic-mean-seeded Wilder smoothing for RSI/ATR. True Range is
undefined without a previous close; n-period RSI/ATR first appear on bar n+1.
Use sample standard deviations (ddof=1) and annualize return volatility by sqrt(252)
by default. Zero-denominator z-scores, all-flat RSI, and all-zero relative-volume
windows remain NaN. These are measurements without signal thresholds.

Reason: Indicator conventions must be reproducible and testable rather than
implicit dependency defaults. pandas/NumPy suffice without a new TA dependency.
Wilder averages retain a decaying dependency on the initial history/seed.

## ADR-009 — Benchmark returns use matched timestamp endpoints

Date: 2026-09-30. Status: Accepted.

Decision: Require an explicit single-ticker benchmark, normally SPY. Relative
returns compare the stock and benchmark over the stock's exact n-bar endpoints;
either missing benchmark endpoint yields NaN. Compute market context on the
benchmark's own history, then join on exact session date without filling.

Reason: Independently shifting stock/benchmark rows can compare different periods
when calendars differ. Context must retain benchmark history before stock inception.
The date-based convention assumes both instruments' bars are available at the
calculation time; cross-market publication timing needs additional metadata.

## ADR-010 — Prior-only ticker-relative percentile candidates

Date: 2026-09-30. Status: Accepted.

Decision: Define DipSignal V1 components using the lower empirical tail of each
ticker's own drawdown, price z-score, low-distance, and SPY-relative-return history.
Shift each feature by one observed bar before computing a linear-interpolated
rolling quantile. Defaults are 252 prior bar positions, at least 126 valid values
per feature, and quantile 0.20. Missing slots do not compress the window.

Reason: Different equities have different feature distributions. A transparent
self-relative hypothesis avoids immediately optimizing fixed technical-analysis
cutoffs and prevents the current observation from influencing its own threshold.

Consequences and limitations: These defaults are not optimality claims. Features
are correlated; component counts are not probabilities or independent confirmations.
Inclusive ties and changing distributions mean activation frequency need not equal
the nominal quantile. Data-vintage and survivorship limitations remain. Predictive
quality requires a separately specified empirical evaluation, not threshold tuning
to make descriptive frequencies look attractive.

## ADR-011 — Complete-row eligibility and observed condition entries

Date: 2026-09-30. Status: Accepted.

Decision: Require all four current features and all four historical thresholds
before a condition can be true, plus at least three active components by default.
Keep separate count, readiness, condition, and per-ticker rising-edge event outputs.

Reason: Missing benchmark/history must not masquerade as evidence of a dip. Separate
conditions and entries expose persistent depression without counting every day as
a fresh discovery or introducing a backtester's position/cooldown state.

Consequences and limitations: Incomplete rows are false conditions and break runs;
the next qualifying row is a new observed entry, not necessarily a new economic
episode. Absent sessions insert no rows. Entries are not statistically independent
trades, and no execution or outcome is implied. Availability is after the current
close; a later backtest must generally execute at t+1 or later.

## ADR-012 — Separate next-open outcomes and split-bounded execution research

Date: 2026-09-30. Status: Accepted.

Decision: Keep forward outcomes/trade ledgers separate from causal features and
signals. Enter on the next observed same-ticker open; entry day counts as holding
bar 1. Use configurable first-hit target/stop/time exits, conservative same-bar
ambiguity, open-price gap fills, and explicit adverse per-side costs. Preserve
every candidate with a completion/exclusion status. Require the full horizon or
maximum holding window within the signal's chronological split before evaluation.

Reason: After-close data cannot justify a same-close entry. Daily OHLC cannot
reconstruct intraday ordering. Uniform full-window censoring avoids selectively
retaining quick wins/losses near dataset/split ends, and prevents research labels
from consuming validation/test prices. Separate outcome tables prevent accidental
reuse as predictive features. Fixed exit defaults remain illustrative hypotheses.

Consequences: Some observable early exits near boundaries are deliberately excluded;
no terminal liquidation is fabricated. Open exits use only exit-day open in excursion
measurement; intraday exit excursions are explicitly full-bar envelopes that may
include post-fill movement. Non-overlapping-per-ticker streams do not provide an
allocated multi-stock portfolio. Observe all known data-vintage limitations.

## ADR-013 — Descriptive comparisons with dependence-aware uncertainty

Date: 2026-09-30. Status: Accepted.

Decision: Freeze V1 and illustrative exits before inspecting EXP-001. Use common
60/20/20 unique-session-date splits, unconditional ready/non-condition stock controls,
and SPY returns matched to each stock's exact entry and endpoint dates. Estimate
mean uncertainty using seeded circular blocks of 20 observed date clusters,
keeping same-day stock rows together. Report subgroup outcomes without selecting
parameters. Require at least two blocks for an interval.

Reason: Chronology, same-interval comparisons, and visible missing/exclusion counts
are more informative than a single pooled positive return. Overlapping events and
simultaneous equity moves invalidate naive independent-trade interpretations.

Consequences: Block-bootstrap coverage remains an assumption, not a significance
claim; ticker/date composition can differ across baseline samples. Regular-period
Sharpe/Sortino require an explicit capital-return series. Only single-ticker sorted
non-overlapping trades may receive hypothetical reinvestment/trade-close drawdown
metrics; no pooled portfolio curve is fabricated. Reporting the test split consumes
that historical holdout: later tuning must not treat it as fresh out-of-sample data.

## ADR-014 — Retain EXP-001's fixed specification and mixed evidence

Date: 2026-09-30. Status: Accepted.

Decision: Close the initial evaluation foundation with all five stocks, all five
horizons, both trade modes, and both component subgroups reported. Preserve V1's
20th percentile, 252-bar lookback, 126-value minimum, three-of-four requirement,
and the illustrative +10%/-7%/10-bar exits. Do not tune using the reported test split.

Reason: Numerically higher event means are not tests of baseline differences.
Non-overlapping test trades averaged only 0.019% net under the fixed costs;
negative individual-stock results and the weaker validation four-component group
are evidence to retain, not reasons to select a more favorable specification.

Consequences: The historical holdout is consumed, and neither significance of
baseline outperformance nor profitability is established. Recommend a separately
pre-registered robustness / walk-forward milestone with a broader point-in-time
universe and fresh holdout data. That milestone is not implemented or authorized
by completion of EXP-001. Preserve local input snapshots; generated verification
reports stay ignored by Git.

## ADR-015 — Frozen cross-sectional robustness with explicit universe provenance

Date: 2026-09-30. Status: Accepted before EXP-002 outcome evaluation.

Decision: Freeze the EXP-001 signal/exit specification and test all 95 eligible
names in a dated OEF current-holdings snapshot after excluding the inspected
issuers. Use annual expanding history, full-window fold censoring, explicit
membership masks, and predeclared SPY regimes/concentration diagnostics. Separate
static membership from interval-format support and genuine point-in-time provenance.

Reason: EXP-001's near-zero test net expectancy motivates testing generalization,
not tuning a winner. Current constituents provide broader but survivor-biased
cross-sectional evidence; no fresh temporal holdout is claimed. Prior publication
of the protocol prevents adapting universe, horizons or interpretation to outcomes.

Consequences: All data-quality failures and negative results remain visible.
Per-ticker and contribution summaries accompany pooled means. Existing forward
calculations were vectorized with unchanged output semantics for broader control
samples; the full EXP-001 report reproduced exactly. No signal/feature change,
parameter search, portfolio model, scanner or future-signal archive is introduced.

## ADR-016 — Retain the failed EXP-002 breadth criterion

Date: 2026-10-01. Status: Accepted after fixed-specification reporting.

Decision: Retain the frozen benchmark and every negative fold/ticker. Report the
directional breadth criterion as failed because only 36/74 ticker ten-bar matched-SPY
excess means are positive, despite favorable pooled means and 5/6 favorable fold
comparisons. Evaluate the separately registered barrier sign criterion separately:
5/6 positive fold means and 52/74 positive ticker net expectancies satisfy it.

Reason: Pooled descriptive improvements cannot override a predeclared criterion,
establish significance of baseline differences, or justify automatic model tuning.

Consequences: The universe remains explicitly static/survivor-biased, the 21 OHLC
exclusions remain visible, and the newly inspected history is consumed. Data-quality
and historical-membership work plus prospective signal preservation are recommended
next, not implemented or treated as authorized model/scanner development.

## ADR template

- ID and title:
- Date / status:
- Decision:
- Reason:
- Consequences and limitations:
- Supersedes (if applicable):

## ADR-017 - Diagnose data vintages without retroactively repairing experiments

Date: 2026-10-01. Status: Accepted under EXP-003 registration `8c55fbc`.

Decision: Preserve complete newly returned adjusted DataFrames before validation,
separately from the frozen historical market cache. Label new acquisitions as new
vintages because original rejected EXP-002 responses were not preserved. Keep
strict OHLC checks and all original exclusions/results unchanged. Report exact
relations, sessions, values, relative errors and floating-point spacing units.

Reason: All 29 newly observed violations are one-spacing close-boundary differences,
but nine of the 21 formerly excluded names now pass. These facts motivate a
numerical/provider investigation, not a strategy-driven sample repair. The original
bytes cannot be reconstructed from current responses. No ingestion defect requiring
a behavior change was established in this milestone.

Consequences: Recommend separately authorized paired unadjusted/adjusted evidence
and identity/membership validation before any explicit numerical-policy change.
Current constituent dates and interval schemas do not establish PIT provenance.
No returns were recalculated, no tolerances changed and no losing names removed.

## ADR-018 - Preserve decisions before execution with explicit archive finalization

Date: 2026-10-01. Status: Accepted under EXP-003 registration `8c55fbc`.

Decision: Use a manually invoked, collection-only archive for all 95 registered
names. Pin XNYS calendar support rather than infer sessions from weekdays. Publish
immutable intent, input and result records; only a receipt timestamp sampled after
the result write can establish timely publication. Preserve snapshot bytes, source
provenance, code/config hashes and every non-event/failure. Frozen configuration is
enforced at both the CLI and direct run-creation API.

Reason: A timestamp assigned before a long download/write can falsely claim a
signal existed before the next open. Mutable caches and absent runs cannot serve
as an auditable temporal holdout. An explicit late/stale/replay/correction record
is preferable to silently reconstructing an apparently timely signal.

Consequences: Identical retries return the original; changed vintages use linked
corrections and never replace the primary cohort. Interrupted runs remain
ineligible and recover only as explicit abandoned attempts. Hashes/atomic writes
provide local consistency, not independent timestamps or tamper-proof evidence.
The first eligible session is October 1; review is barred until the registered
future date/coverage gate and requires separate authorization. No outcome scoring,
live scanning, broker execution or strategy tuning is implemented.

## ADR-019 - Present verified research through an offline static frontend

Date: 2026-10-01. Status: Accepted under the research frontend task.

Decision: Use React/TypeScript, Vite, Recharts and plain CSS. A read-only Python
adapter verifies preserved result/input hashes and exports compact, versioned JSON.
Load one ticker history on demand and keep signal-time fields separate from future
outcomes. Render experiment protocols and the research timeline from canonical
Markdown instead of copying their results into UI components.

Reason: The interface should expose quantitative evidence and failed hypotheses,
without becoming a second research engine or implying a live trading service.
Existing Python APIs remain the source of truth. A static interface requires no
additional backend service, database, credentials or scheduler.

Consequences: Gross/net, event/trade, consumed historical OOS and genuine
prospective classifications are explicit. Missing artifacts fail honestly. The
archive is verified and displayed, never collected or scored. Browser exports,
raw data, screenshots and build output remain ignored. Hashes provide consistency
checks, not independent authenticity. No frozen strategy, protocol, exclusion,
historical metric or cache is changed. Public deployment is separate work.

## ADR-020 - Brief answers first, evidence available on request

Date: 2026-10-01. Status: Accepted for frontend usability.

Decision: Show each experiment as question, test, result and limitation. Keep the
original record and exact tables behind optional controls. Explain metrics on tap
with short, explicitly hypothetical examples. Use plain language across views.

Reason: The frontend must help its owner learn, not require reading an entire
research report before understanding a result. Negative findings and uncertainty
must stay visible in the short version.

Consequence: Editorial summaries are presentation metadata, never alternate
statistics. Frozen source data and experiment records are unchanged. A separate
tech/AI research proposal is documented without running a subgroup evaluation.

## ADR-021 - Separate ATR-sized exits from frozen V1

Date: 2026-10-02. Status: Accepted; EXP-004 preregistered, not run.

Decision: Keep V1's fixed barriers unchanged. Prototype ATR(14)-scaled levels
using only signal-session data, and select candidate multipliers only on the
research split. Treat net mean return as EV and report its win/loss decomposition.
Do not use inspected validation/test outcomes to select exits; prospective
comparison waits for EXP-003's review gate and separate authorization.

Reason: Exit rules may reasonably scale with each stock's recent range, but
choosing a rule on consumed holdouts would make its apparent evidence optimistic.

Consequence: The calculator and EV diagnostics add no selected exit settings or
performance claims. V1, EXP-001/002 results and EXP-003 archive remain unchanged.
