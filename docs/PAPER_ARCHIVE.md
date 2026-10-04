# Manually invoked prospective signal archive

This is the collection-only foundation registered in
[EXP003_PROTOCOL.md](EXP003_PROTOCOL.md), commit `8c55fbc`. No scheduler, alerts,
broker, live scanner or outcome evaluator is present. Both historical experiments
are consumed. This archive does not make V1 profitable or its static universe PIT.

## Operating protocol

The 95 requested EXP-002 names are fixed in `config/exp003.json`, including every
previous data failure and losing stock. SPY supplies context only. Frozen source
and configuration hashes prevent parameter/universe drift. The full existing
history starts 2016-09-29; V1 uses the unchanged feature defaults, thresholds and
rising-edge semantics. New provider vintages may revise that history, so retain
all bytes used in each decision. No old research cache is refreshed.

For each signal session from **2026-10-01**, manually invoke collection between
00:15 America/New_York on the next calendar date and the next scheduled regular
open. Normal open is 09:30 Eastern. Use the session date, not your local date:

```powershell
# Example for the October 1 close, run on October 2 before the regular open.
.\.venv\Scripts\python.exe -W error -m scripts.archive_signals collect --session 2026-10-01 --run-id 2026-10-01
.\.venv\Scripts\python.exe -W error -m scripts.archive_signals verify --run-id 2026-10-01 --replay
.\.venv\Scripts\python.exe -W error -m scripts.archive_signals coverage
```

This command uses `download_raw_data`, strict `clean_data`/Parquet validation,
`build_features`, `build_signals` and the existing membership mask. It retrieves
SPY and all 95 stocks; raw returned frames are quarantined before validation.
Each failure is recorded independently. A failed benchmark prevents dependent
decisions. Missing session bars are stale, with no substituted decision.

The actual UTC clock is recorded in production; there is no CLI timestamp override.
Calendar source is pinned `exchange-calendars==4.13.2`, XNYS regular sessions;
see its [source](https://github.com/gerrymanoim/exchange_calendars) and the
[NYSE schedule](https://www.nyse.com/markets/hours-calendars). Holidays, early
closes and DST are explicit. XNYS is a common US session proxy, not a halt feed
or exchange guarantee. Calendar facts and version are saved per run. Unexpected
closures require explicit correction; operations should check exchange notices.

Prospective classification requires current signal-date bars for both stock and
SPY, retrieved after their scheduled close and before calculation, a clean recorded
code revision, frozen settings and publication before the next scheduled open.
The result is written and fsynced **before** the publication timestamp is sampled;
a separate receipt binds that timestamp to the result hash. Crossing the open
during calculation or writing makes the record late. No receipt means interrupted,
not prospective. The receipt itself may be written later: it timestamps the already
published original result, not a later simulated signal. Local clock accuracy is
an assumption, not independently witnessed evidence.

Readiness=false remains a preserved prospective observation when timing and data
are valid; it is not an event. Every run retains all requested stocks, non-events,
failures and component/feature/threshold values. There is no t-close execution.
The registered later evaluator assumes next observed same-ticker open and the
unchanged +10%/-7%/10-bar model and per-side 1 bp commission/5 bp slippage.
The scheduled open is a conservative recording deadline; actual same-ticker
execution may be unavailable or delayed and must not be invented.

## Replay, retries and corrections

```powershell
# Explicit historical replay; never prospective, even if its date is recent.
.\.venv\Scripts\python.exe -W error -m scripts.archive_signals collect --session 2026-09-28 --run-id exp003-replay --replay-cache data/market
# Mark an interrupted attempt without promoting its partial signals.
.\.venv\Scripts\python.exe -W error -m scripts.archive_signals recover --run-id interrupted-run
# New acquisition/version; preserve earlier bytes and explain the change.
.\.venv\Scripts\python.exe -W error -m scripts.archive_signals collect --session 2026-10-01 --run-id 2026-10-01-correction --corrects 2026-10-01 --reason "New provider vintage"
```

Run IDs are explicit stable keys. Repeating a sealed run with the same identity
verifies and returns the original, without network calls or new signals. To use
changed input bytes, choose a new key, parent and reason. Identity conflicts raise.
The first run reserves its session atomically; a correction reserves one successor
of its parent. Two concurrent primaries or competing successors cannot silently
replace each other. Only one process should operate a given run key at a time.

Corrections are always classified `correction`, preserving their actual timestamp;
they do not enlarge or replace the original prospective holdout. A later authorized
review may discuss them separately. Coverage uses original attempts only. A missing
run, interrupted attempt, failed/partial run and complete zero-event run are distinct.
An interrupted intent/result cannot be silently resealed: mark recovery, then use
a new correction key. Recovery is idempotent and never alters old bytes. If a process
dies after a session reservation but before intent creation, retry the same key and
identity; the untouched reservation prevents a competing primary.

## Stored schema and integrity

All generated contents are ignored under `data/paper_archive/`:

- `objects/<sha256>`: immutable exact raw/validated snapshot bytes and config JSON.
- `sessions/<date>.json`, `successors/<run-id>.json`: atomic identity reservations.
- `runs/<id>/intent.json`: UTC start, session/calendar facts, universe/config hash,
  code revision/dirty status/source hashes, mode and correction reference/reason.
- `runs/<id>/inputs/<ticker>.json`: retrieval provenance, snapshot hashes and status,
  including validation/download errors saved as each symbol finishes.
- `runs/<id>/result.json`: all 95 decision records, input descriptors, calculation
  timestamp, completion status and intent hash. Record IDs are `run-id:ticker`.
- `runs/<id>/receipt.json`: actual post-publication timestamp, result hash and
  per-ticker prospective/retrospective/early/late/stale/unavailable/unverifiable/
  correction classification.
- `runs/<id>/recovery.json`: an explicit abandoned/interrupted attempt marker.

JSON envelopes have SHA-256 hashes and prohibit NaN/Infinity; warm-up values are
nulls. Atomic publication uses a same-directory temporary file, fsync and a hard
link that refuses overwrite. NTFS/ext4-style hard-link support is required; there
is no unsafe fallback. Leftover `.pending-*` files are never automatically promoted.
Interrupted acquisitions may leave unreferenced objects, which are retained.
`verify --replay` verifies hashes and recomputes decisions offline from preserved
vintages. Hash checks detect changes relative to stored hashes; someone who can
rewrite all files/hashes or the system clock can defeat them. Local storage is
not tamper-proof, independently timestamped or a power-loss-safe replicated system.
Maintain independent backups. No market snapshots or private run data belong in Git.

Raw here means the complete DataFrame returned by the existing downloader, **after
yfinance adjustment**, before project validation. It is not the original HTTP
response or an unadjusted exchange tape. Retention improves reproducibility but
does not remove adjusted-price revisions, identity limitations or survivorship bias.

## Future outcome review

No outcomes are calculated or attached here. First review is no earlier than
2027-04-01, subject to separate authorization, at least 100 scheduled sessions
and completed timely original runs on at least 80% of those sessions. A complete
timely run requires all requested decisions available and prospectively classified;
data-quality failures can make this demanding threshold fail. If unmet, defer to
2027-10-01, not a date chosen after viewing returns. This task does not wait for data.

Later outcomes must be separate versioned records referencing original signal IDs,
outcome input hashes and the fixed review cutoff. Retain missing/unfavorable results;
apply registered full-window censoring and costs; report collection coverage and
selection limitations. No rolling performance peeking, favorable optional stopping
or tuning on the growing holdout is authorized. Further review/extensions require
new authorization and, where applicable, new prospective registration.

## Additional decision context

After a manual run is sealed, invoke `python -m scripts.archive_context --run-id
<original-run-id>` before its intended next open. This command is offline and
uses retained vintages, not refreshed caches. It preserves ATR, volume, momentum,
weakness, benchmark state, causal SPY regime and mature prior dip-zone context for
events and non-events. Existing V1 thresholds and input/code/configuration hashes
stay linked through the original result hash. The scheduled next open is an
**expected execution opportunity**, not an observed entry fill.

`config/archive_context.json` defines the context. No adaptive exit policy is
activated: EXP-004 has fold-varying selections, so a single prospective policy
needs a separate advance registration. Future comparisons must use the exact same
original prospective signal IDs. No future outcome fields enter this sidecar.

Ignored `contexts/` and `context_receipts/` retain immutable values and separate
publication seals. Original run bytes never change; retries return original
context. Changed bytes, parents or input identities fail checks. Corrections use
explicit new run/version IDs. Interrupted publication without a seal remains
unverifiable; recovery cannot promote it into the prospective cohort.

Calculation timestamps are actual UTC readings after computation; seal timestamps
follow publication. `prospective_context` requires an original prospective signal,
clean code, valid chronology and publication before the next open. Late enrichment
is `retrospective_context` and never changes the original signal classification.
Hashes detect alterations relative to retained hashes, not adversarial tampering.
No genuine prospective record was manufactured for this extension.
