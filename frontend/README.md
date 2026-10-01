# DipSignal Research terminal

Local, read-only React + TypeScript + Vite frontend. Python owns research
calculations; the browser filters and visualizes verified exports. No server,
collector, trading integration, or credentials are needed.

From the repository root, using the project's Python environment:

```powershell
.\.venv\Scripts\python.exe -m scripts.build_dashboard_data
cd frontend
npm.cmd ci
npm.cmd run dev
```

Open the localhost URL printed by Vite. On non-Windows systems use `npm`.
`npm.cmd test` runs UI tests; `npm.cmd run build` creates a local production build.

The exporter is offline. It reads preserved EXP-001/002 results, their snapshots,
EXP-003 diagnostics and the paper archive. These inputs and all browser exports
are ignored by Git. A fresh clone without private/local artifacts shows explicit
unavailable states and can still export the research documentation. It never
substitutes demonstration returns or downloads new market data.

The manifest atomically selects a content-addressed generation. Source artifacts
and browser files are hash checked. Each ticker history loads only when selected.
Use `--as-of <UTC timestamp>` for deterministic coverage exports; this is not a
signal collection timestamp. Re-export after an authorized archive collection.

Serve the site through Vite or another HTTP server, not `file://`. Exports contain
historical data and local archive records: review data licensing and privacy
before choosing to publish them. This task does not deploy the site.
