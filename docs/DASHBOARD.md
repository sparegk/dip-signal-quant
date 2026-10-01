# Quantitative research terminal

## Reading the site

Start with **Overview → Signal Explorer → Experiments → Robustness**.
Experiments now shows a short **Question / Test / Result / Limitation** brief.
Exact tables and the original record open on request. Metric names are clickable
on desktop and mobile; numerical examples are labeled as examples, not results.

Editorial briefs live in `frontend/src/content/experiments.json`. Their displayed
statistics still come from the Python export. Full protocols remain unchanged.

Design references:
- [NN/g: progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/):
  show the essentials first, reveal detail when requested.
- [Our World in Data](https://ourworldindata.org/about): explain what a chart shows
  and why it matters; keep the evidence and sources accessible.
- [Portfolio Visualizer](https://www.portfoliovisualizer.com/backtest-portfolio):
  make comparisons explicit. This project still reports event/trade outcomes,
  not an allocated portfolio.

These inspired the presentation, not strategy rules or performance claims. No
third-party code, copy or assets were imported. The proposed next research focus
is [large-cap tech and AI](RESEARCH_FOCUS.md); no new group evaluation has run.

The frontend is a read-only local research interface. It does not collect market
data, evaluate new strategy specifications, score candidates, place orders or
inspect prospective returns. DipSignal V1 and all three experiments remain frozen.

## Run locally

Use the existing Python environment and Node.js 24 (tested). From the repository
root:

```powershell
.\.venv\Scripts\python.exe -m scripts.build_dashboard_data
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open <http://127.0.0.1:5173>. On other platforms use `npm` and the corresponding
Python environment path. `npm.cmd run build` creates a static production build;
`npm.cmd run preview` serves it locally. No API server or account is required.
The development and preview servers bind to loopback by default.

A fresh clone has code and documentation but not ignored research artifacts.
The exporter still produces documentation and explicit missing-data states.
If no export exists at all, the site explains how to build it. It never inserts
synthetic returns or starts downloading data. Reuse preserved experiment inputs
and reports; see the existing experiment reproduction guides if they are absent.

## Architecture and sources

React/TypeScript with Vite keeps the interface independent of the Python research
environment. Recharts supplies responsive analytical charts. React Markdown with
GitHub table support renders the canonical research record. Plain CSS provides a
neutral, compact layout without a UI framework. Hash navigation works on a static
server; research views and ticker histories load on demand.

`scripts/build_dashboard_data.py` is the offline adapter and sole dashboard data
producer. It does not implement a second backtester or feature engine.
It reuses the archive's registered-protocol checks and refuses configuration or
frozen source drift before publishing any output.

| View/source | Adapter behavior |
| --- | --- |
| EXP-001 `data/exp001-verification.json` | Uses saved summary statistics; checks the six snapshot hashes and frozen feature/signal code; reconstructs detailed signal/outcome ledgers through existing Python APIs with the saved chronological boundaries. No new specification or summary fitting. |
| EXP-002 `results/exp_002/metadata.json` and artifacts | Verifies all registered artifact hashes, reads existing summary CSVs and event/trade/observation Parquet files. Produces display histograms, joins and baseline differences in Python. |
| EXP-003 `data/exp003/diagnostic_authorized/` | Runs the existing audit renderer's retained-vintage verification, then exports all ticker summaries and exact violation values. |
| `data/paper_archive/` | Verifies each run and retained input; preserves actual classification, record status, run completion, non-events, failures, hashes and coverage. Does not calculate outcomes. Raw local exception paths are omitted. |
| `config/exp003.json` | Supplies the registered universe, dates and collection/review protocol. |
| `docs/*.md`, `ROADMAP.md` | Supplies experiment protocol/result text, methodology, research timeline and milestone states. |

The feature catalog describes the current Python feature definitions. Its entries
are educational metadata, not an alternative implementation. Quantitative values,
thresholds, returns and summaries come from Python. Browser operations are limited
to presentation, sorting, date/ticker/component filters and formatting.

## Export format and integrity

Generated files live under ignored `frontend/public/data/`. `manifest.json`
atomically selects a content-addressed generation and lists SHA-256 hashes for
the dashboard and every ticker file. The browser checks the fetched file's hash
before using it. Existing generation files are immutable; an interrupted export
does not switch the manifest to an incomplete generation. Hashes detect accidental
changes relative to the manifest; they are not signatures or tamper-proof evidence.

The compact columnar ticker schema separates `known_at_signal` from
`future_outcomes`. No Parquet file enters the browser. This local dataset exports
79 ticker histories across the two experiments, roughly 108 MB uncompressed in
total, but the browser requests only the selected ticker (plus the approximately
2.3 MB dashboard index). Old generations remain locally for safe publication.

Given identical sources and the same `--as-of` cutoff, the export is deterministic:

```powershell
.\.venv\Scripts\python.exe -m scripts.build_dashboard_data --as-of 2026-10-01T00:00:00Z
```

That cutoff controls coverage reporting only. It never changes archived collection
timestamps or turns historical observations into prospective records. Refresh the
export after an authorized manual collection; this frontend does not run one.

## Research interpretation in the interface

- Overview distinguishes gross event returns from net trade outcomes. Baseline
  differences are percentage points. Paired SPY excess uses the existing paired
  statistic, not a subtraction of potentially unpaired aggregate means.
- Robustness retains failed breadth, negative years, all losing tickers, the
  concentration denominator and the static-universe survivorship limitation.
  Contribution sums are equal-notional fractions, not portfolio returns.
- Signal Explorer exposes historical price context, event/condition filters,
  component values, prior thresholds and readiness. A separate future-outcome
  section retains each horizon's and trade mode's censoring status. Entry dates
  and prices belong to that future section, not the signal-time decision.
- EXP-001 supports research/validation/test filters. EXP-002 histories are its
  exported annual OOS observations, not the earlier expanding-history rows.
  Both inspected historical samples are consumed.
- Paper Archive defaults to genuinely prospective records. Historical replay has
  its own tab; late/stale/unavailable timing classifications remain separate.
  The current archive has zero genuine prospective records and makes no current
  actionable-signal claim. Missing coverage and failed inputs are not non-events.
- Data Quality keeps new diagnostic vintages separate from the unpreserved
  original rejected responses. No remediation is applied by the interface.
- Metric definitions explain uncertainty and limitations. No synthetic edge
  score, confidence estimate, alpha claim or portfolio Sharpe is introduced.

## Verification and operational limits

```powershell
.\.venv\Scripts\python.exe -m pytest -q -W error
cd frontend
npm.cmd test
npm.cmd run format:check
npm.cmd run build
npm.cmd run test:browser
```

Ordinary adapter and UI tests use deterministic offline fixtures. Browser smoke
tests use the already-exported local research data, never download market data,
and skip when the manifest is absent. They exercise all pages, the negative fold,
archive separation, signal/feature selection and mobile navigation. On Windows
they use installed Microsoft Edge; elsewhere install Playwright's Chromium once
with `npx playwright install chromium`. Screenshots/traces remain ignored.

This is a local historical-research interface, not a live service. It has no auth,
API, scheduler or deployment. Exported data and screenshots may carry research
data licensing/privacy restrictions; no dataset is published or committed by this
task. Original snapshots remain separate from frontend artifacts. A later public
demo should use a deliberately approved, provenance-preserving publication subset.
