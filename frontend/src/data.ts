export type Row = Record<string, string | number | boolean | null>
export type Manifest = { schema_version: number; generation: string; as_of: string; dashboard: string; series: Record<string, string>; sha256: Record<string, string> }
export type Feature = { key: string; group: string; window: string; formula: string; interpretation: string; warmup: string; unit: string; data: string; availability: string; used_in_v1: boolean }
export type Series = { ticker: string; experiment: string; known_at_signal: Row[]; future_outcomes: Record<string, { horizons?: Row[]; trades?: Row[] }>; availability: string }
export type ArchiveRecord = { record_id: string; ticker: string; session: string; run_id: string; classification: string; status: string; published_at: string; code_revision: string; config_hash: string; input_hash: string | null; retrieved_at: string | null; values: Row | null; error: string | null; outcome: Row | null }
export type Archive = { status: string; config: { universe: string[]; effective_session: string; review_dates: string[] }; runs: Row[]; records: ArchiveRecord[]; coverage: Row[]; prospective_count: number; retrospective_count: number; non_event_count: number; failure_count: number; as_of: string }
export type Experiment = { id: string; title: string; status: string; body: string; doc: string }
export type Exp2 = {
  status: 'available'; source_sha256: string;
  metadata: { requested_count: number; usable_count: number; excluded_count: number; usable_tickers: string[]; requested_tickers: string[]; code_commit: string; config_sha256: string; concentration: Record<string, Row>; config: { start: string; end_exclusive: string; source_as_of: string; signal_parameters: Row; barrier_parameters: Row } };
  tables: Record<string, Row[]>; comparison: Row[]; folds: Row[]; histograms: Record<string, Row[]>; exit_counts: Row[]; event_ledger: Row[]; frequency: Row;
  criteria: { breadth_passed: boolean; positive_excess_tickers: number; defined_tickers: number; favorable_folds: number; fold_count: number; concentration_threshold: number }
}
export type Dashboard = {
  schema_version: number; as_of: string; last_research_update: string; feature_catalog: Feature[];
  exp001: { status: string; reason?: string; comparison?: Row[]; report?: { splits: Row[]; trade_summaries: Row[]; code_commit: string; snapshots: Record<string, unknown>; split_parameters: Row } };
  exp002: Exp2 | { status: 'missing'; reason: string };
  audit: { status: string; reason?: string; summaries?: Row[]; rows?: number; affected_rows?: number; violations?: Row[] };
  archive: Archive; experiments: Experiment[]; documents: Record<string, string>; research_log: { date: string; title: string; body: string }[]; roadmap: { title: string; status: string }[]
}

const dataBase = `${import.meta.env.BASE_URL}data/`
export async function readJSON(path: string, hash?: string, signal?: AbortSignal) {
  if (!/^[\w/.-]+$/.test(path) || path.split('/').includes('..')) throw new Error('Invalid export path')
  const response = await fetch(dataBase + path, { signal, cache: 'no-store' })
  if (!response.ok) throw new Error(response.status === 404 ? 'Research export not found. Run the Python dashboard exporter.' : `Research data request failed (${response.status}).`)
  const bytes = await response.arrayBuffer()
  if (hash) {
    const actual = [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('')
    if (actual !== hash) throw new Error('Export integrity check failed. Rebuild the dashboard data.')
  }
  try { return JSON.parse(new TextDecoder().decode(bytes)) } catch { throw new Error('Invalid research export. Run the Python dashboard exporter.') }
}
export async function loadDashboard(signal?: AbortSignal): Promise<{ manifest: Manifest; data: Dashboard }> {
  const manifest = await readJSON('manifest.json', undefined, signal) as Manifest
  if (manifest.schema_version !== 1 || !manifest.sha256?.['dashboard.json']) throw new Error('Unsupported dashboard manifest')
  const data = await readJSON(manifest.dashboard, manifest.sha256['dashboard.json'], signal) as Dashboard
  if (data.schema_version !== 1 || !Array.isArray(data.experiments) || !data.archive || !data.exp002) throw new Error('Invalid dashboard schema')
  return { manifest, data }
}
export async function loadSeries(manifest: Manifest, experiment: string, ticker: string, signal?: AbortSignal): Promise<Series> {
  const key = `${experiment}/${ticker}`
  const path = manifest.series[key]
  if (!path) throw new Error('No preserved history for this ticker and experiment.')
  const raw = await readJSON(path, manifest.sha256[`series/${key}.json`], signal)
  if (raw.schema_version !== 1 || raw.ticker !== ticker || raw.experiment !== experiment || !Array.isArray(raw.known_at_signal?.columns) || !Array.isArray(raw.known_at_signal?.rows)) throw new Error('Invalid ticker export')
  const columns: string[] = raw.known_at_signal.columns
  const known: Row[] = raw.known_at_signal.rows.map((row: unknown[]) => {
    if (row.length !== columns.length) throw new Error('Invalid ticker row width')
    return Object.fromEntries(columns.map((column, i) => [column, row[i]]))
  })
  return { ...raw, known_at_signal: known }
}
export const number = (value: unknown): number | null => typeof value === 'number' && Number.isFinite(value) ? value : null
export function format(value: unknown, kind = 'percent'): string {
  const n = number(value)
  if (n === null) return '—'
  const scaled = kind === 'percent' || kind === 'pp' ? n * 100 : n
  const digits = kind === 'integer' ? 0 : kind === 'price' ? 2 : 3
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits,
    signDisplay: kind === 'percent' || kind === 'pp' ? 'exceptZero' : 'auto' }).format(scaled) + (kind === 'percent' ? '%' : kind === 'pp' ? ' pp' : '')
}
export const tone = (value: unknown) => typeof value === 'number' ? (value > 0 ? 'positive' : value < 0 ? 'negative' : '') : ''
export type Filters = { start: string; end: string; components: string; kind: string; split: string }
export function filterObservations(rows: Row[], filter: Filters): Row[] {
  return rows.filter(row => (!filter.start || String(row.date) >= filter.start) && (!filter.end || String(row.date) <= filter.end)
    && (filter.components === 'all' || String(row.dip_component_count) === filter.components)
    && (filter.kind === 'all' || (filter.kind === 'event' ? row.dip_event_v1 : row.dip_condition_v1))
    && (filter.split === 'all' || row.split === filter.split))
}
export const docURL = (name: string) => `https://github.com/sparegk/dip-signal-quant/blob/main/docs/${name}.md`
