# EXP-003 registration: data audit and prospective preservation

Registered 2026-10-01 (project timezone Europe/Athens), before new diagnostic
acquisition or prospective collection. Commit and push this protocol and
`config/exp003.json` first. Append findings and implementation corrections later;
do not rewrite this registration after observing diagnostic data.

## A. Historical data-quality and universe-provenance audit

Question: What numerical defects accompany the 21 EXP-002 OHLC exclusions, and
what provenance is missing for historical membership research? This is **not a
new historical strategy-performance evaluation**. EXP-001 and EXP-002 historical
samples are consumed. EXP-002's failed breadth criterion, negative 2022 and 22
negative ticker expectancies remain part of the record.

Use the existing acquisition audit and all 21 excluded tickers, without replacements.
Record original error messages and whether original rejected responses exist.
If absent, one new diagnostic request per ticker through `download_raw_data` for
2016-09-29 to 2026-09-29 exclusive is a **new diagnostic vintage**, not evidence
of the exact original response. Preserve the entire returned DataFrame, metadata,
retrieval timestamp and content hash in ignored quarantine before strict cleaning.
Network failures remain findings; an infrastructure retry must be disclosed and
must not select responses based on quality. No refresh of `data/market` is allowed.

Report each violated low/high/open/close relation, affected session and OHLC values,
row count/fraction, absolute gap, gap divided by the larger absolute operand, and
gap in floating-point spacings at that magnitude. Report temporal spread and all
violations, including nonnumeric/nonfinite/nonpositive/schema defects if encountered.
Compare discrepancy sizes descriptively; no diagnostic size bucket changes
ingestion acceptance. Distinguish facts from roundoff, provider rounding,
adjustment, corporate-action, or identifier hypotheses. Identical positive
rescaling preserves OHLC order mathematically, though finite precision matters.
Recommend further remediation evidence independently of strategy outcomes.

No widening tolerance, clipping, filling, row deletion, ticker substitution,
reinsertion into EXP-002 or return-based selection is authorized. A genuine audit
implementation bug may be corrected with regression tests and a dated explanation.

Audit the frozen September 29 OEF source, deterministic 101-row to 95-symbol rule,
share classes, symbol normalization and important identity/listing discontinuities.
Investigate official historical membership/data providers for coverage, permanent
identifiers, availability/revision metadata, access and licensing. Do not purchase
or accept contracts. Existing `[start,end)` membership support is a format, not
proof of point-in-time provenance. Current holdings cannot reconstruct past members.

## B. Prospective paper-signal preservation

Purpose: preserve decisions and unavailable observations before their possible
execution, without inspecting performance. Effective signal session **2026-10-01**;
earlier dates are replay only. The universe is the exact frozen **95 requested
EXP-002 names**, not the 74 passing names or 52 historically positive names. SPY
is benchmark-only. Universe changes require a separately registered amendment and
new version; do not retrospectively alter eligibility. Static survivor selection
remains a limitation even for this genuinely forward collection.

Frozen V1: unchanged feature/signal source hashes and feature defaults, 252 prior
observations, 126 valid minimum, quantile 0.20, three components, existing readiness
and rising-edge semantics. Preserve 1/3/5/10/20-bar horizons, illustrative +10%
target / -7% stop / 10-bar timeout, conservative ambiguity/gap rules, next observed
same-ticker open, 1 bp commission and 5 bp adverse slippage each side. These are
future evaluator assumptions, not implemented outcome calculations in this task.

Use the version-recorded `exchange_calendars` XNYS regular-session calendar and
America/New_York timezone (including DST, holidays and early closes), checked against
[NYSE hours](https://www.nyse.com/markets/hours-calendars). XNYS is the common US
regular-session proxy for this NYSE/Nasdaq universe, not a per-security halt feed.
Preserve the actual calendar close and next scheduled open with each run. Unexpected
closures/calendar corrections require an explicit correction; no invented sessions.

The manual operational expectation is one run for every eligible completed session,
between **00:15 New York time on the next calendar day and strictly before the next
scheduled regular open**. This respects the existing daily downloader's exclusion
of today's New York date. A weekend/holiday does not create a price bar or signal.
The next scheduled open is a conservative publication deadline, not a promise that
an individual halted stock trades then. No scheduler is implemented.

Use actual UTC clocks. Prospective status requires a clean, recorded code revision,
frozen config, completed signal-date stock and SPY bars retrieved after session
close, no input bars later than that date, and durable publication before the next
scheduled open. Provider retrieval confirms local availability, not exchange-level
publication latency. An unknown source timing, missing/stale bar, late publication,
dirty implementation or retrospective/replay invocation cannot qualify. A retry
cannot promote a previously late/replay record. Never backdate timestamps.

Preserve each run intent and final status, all 95 names including non-events and
failures, eligibility/readiness/condition/event/component counts, feature and
threshold values, code/config hashes, raw and validated snapshots, input retrieval
provenance and calendar facts. Benchmark failure blocks dependent decisions.
No run, interrupted run, all failures and valid zero-event run remain distinguishable.
Preserve immutable input bytes separately from refreshable market caches. Adjusted
vintages may contain revisions; archiving one does not make it historically PIT.

Records are append-only. Explicit stable run keys support identical retry without
duplicate signals; conflicts fail. Changed vintages require a new run/version with
a reason and reference to the preceding record. Corrections never erase originals
or retrospectively become timely evidence. Atomic publication and integrity hashes
must detect incomplete bundles, changed records or snapshots; recovery must not
silently finalize an interrupted run with an earlier timestamp. Local hashes are
consistency checks, not tamper-proof or independently witnessed timestamps.

Operational checks may inspect completeness, freshness, schema and integrity,
but **no automatic outcome scoring or accumulating performance dashboard**.
First authorized review is no earlier than **2027-04-01**, and requires at least
100 scheduled eligible sessions with completed, timely runs on at least 80% of them.
Coverage counts are operational, not returns. If unmet, defer to **2027-10-01**;
do not move the date based on returns or event counts. A review still needs separate
authorization. Any extension after that date needs a new prospective registration.

A later evaluator appends separate versioned outcome records referencing original
signal IDs and outcome vintages; preserves missing/unsuccessful signals; uses frozen
execution/cost conventions and complete windows at its fixed cutoff; and reports
missing collection coverage. It must not repeatedly peek, stop on favorable results
or tune on this holdout. This milestone neither waits for nor simulates outcomes.

## Deliverables and interpretation

Version code, deterministic offline tests, configuration and compact documentation.
Ignore quarantine, market/archive snapshots and generated audit/record artifacts.
Tests cover exact discrepancies, raw preservation, vintages, causal timing/calendar,
missing/late/replay records, frozen settings, idempotency/conflicts/corrections,
atomic interruption/recovery, hash integrity, replay and ticker isolation.
Run full pytest with warnings as errors and `pip check`; verify frozen experiment
inputs/configuration and past documented results remain unchanged.

Completion means an audit and tested **manually invoked archive foundation**, not
PIT universe reconstruction, a live scanner, a profitable strategy, or prospective
outcome validation. Make no fresh historical performance claims.
