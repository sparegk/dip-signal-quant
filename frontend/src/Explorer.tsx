import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  Legend,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DataTable, Empty, Note, PageTitle, Section } from './components'
import {
  filterObservations,
  format,
  loadSeries,
  type Dashboard,
  type Filters,
  type Manifest,
  type Row,
  type Series,
} from './data'

const componentKeys = [
  ['drawdown_60d', 'Drawdown', 'dip_drawdown_component', 'percent'],
  ['price_zscore_20d', 'Price z-score', 'dip_price_zscore_component', 'number'],
  ['distance_from_low_20d', 'Distance from low', 'dip_low_proximity_component', 'percent'],
  ['relative_return_10d', 'Relative return vs SPY', 'dip_relative_weakness_component', 'percent'],
]
export function Anatomy({ row }: { row: Row }) {
  return (
    <>
      <DataTable
        rows={componentKeys.map(([key, label, active, unit]) => ({
          label,
          current: format(row[key], unit),
          threshold: format(row[`${key}_threshold`], unit),
          active:
            row[active] === true ? 'Active' : row[active] === false ? 'Inactive' : 'Unavailable',
        }))}
        columns={[
          { key: 'label', label: 'Component' },
          { key: 'current', label: 'Current value' },
          { key: 'threshold', label: 'Prior-tail threshold' },
          { key: 'active', label: 'Activation' },
        ]}
        caption="V1 component values and thresholds"
      />
      <details>
        <summary>Why does a signal fire?</summary>
        <ol className="anatomy">
          <li>Drawdown from the trailing 60-bar closing high is unusually deep.</li>
          <li>The 20-bar price z-score is unusually depressed.</li>
          <li>Price lies unusually close to its trailing 20-bar closing low.</li>
          <li>Ten-bar performance versus SPY is unusually weak.</li>
        </ol>
        <p>
          Each feature must be at or below its own prior 20th-percentile threshold: 252 previous
          observations, at least 126 valid. All four components must be ready; at least three active
          creates a condition. An event is the transition into that condition, not each consecutive
          condition day.
        </p>
        <Note>
          The components are correlated and are not independent probabilities. A component count is
          not a confidence score.
        </Note>
      </details>
    </>
  )
}

export function Signals({ data }: { data: Dashboard }) {
  const [ticker, setTicker] = useState('all')
  const [fold, setFold] = useState('all')
  const [components, setComponents] = useState('all')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const r = data.exp002
  if (r.status !== 'available')
    return (
      <Empty title="Historical ledger unavailable">Export preserved EXP-002 results first.</Empty>
    )
  const rows = r.event_ledger.filter(
    (row) =>
      (ticker === 'all' || row.ticker === ticker) &&
      (fold === 'all' || String(row.fold) === fold) &&
      (components === 'all' || String(row.dip_component_count) === components) &&
      (!start || String(row.timestamp).slice(0, 10) >= start) &&
      (!end || String(row.timestamp).slice(0, 10) <= end),
  )
  return (
    <>
      <PageTitle eyebrow="Historical event ledger · EXP-002" title="Signals in context">
        These are consumed historical research events, not current trade recommendations.
      </PageTitle>
      <Note>
        {data.archive.prospective_count === 0
          ? 'Prospective archive initialized — awaiting first eligible completed session.'
          : `${data.archive.prospective_count} prospective records are available in the Paper Archive.`}{' '}
        <a href="#paper-archive">Open archive →</a>
      </Note>
      <div className="filters">
        <label className="field">
          Ticker
          <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
            <option value="all">All tickers</option>
            {r.metadata.usable_tickers.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        <label className="field">
          OOS fold
          <select value={fold} onChange={(e) => setFold(e.target.value)}>
            <option value="all">All folds</option>
            {r.folds.map((f) => (
              <option key={String(f.fold)}>{String(f.fold)}</option>
            ))}
          </select>
        </label>
        <label className="field">
          Components
          <select value={components} onChange={(e) => setComponents(e.target.value)}>
            <option value="all">All</option>
            <option>3</option>
            <option>4</option>
          </select>
        </label>
        <label className="field">
          From
          <input type="date" value={start} onChange={(e) => setStart(e.target.value)} />
        </label>
        <label className="field">
          Through
          <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} />
        </label>
      </div>
      <Section
        title={`${rows.length.toLocaleString()} matching historical events`}
        note="Select a ticker/date to inspect the signal-time decision and its separately labeled future outcomes."
      >
        <DataTable
          rows={rows}
          columns={[
            { key: 'ticker', label: 'Ticker' },
            {
              key: 'timestamp',
              label: 'Signal session',
              render: (r) => String(r.timestamp).slice(0, 10),
            },
            { key: 'fold', label: 'OOS fold' },
            { key: 'dip_component_count', label: 'Components', format: 'integer' },
            { key: 'regime', label: 'SPY context' },
          ]}
          caption="Historical DipSignal events"
          onSelect={(r) => {
            location.hash = `signal-explorer?experiment=EXP-002&ticker=${r.ticker}&date=${String(r.timestamp).slice(0, 10)}`
          }}
        />
      </Section>
    </>
  )
}

function History({
  rows,
  feature,
  unit = 'price',
  threshold = false,
  events = [],
  onSelect,
}: {
  rows: Row[]
  feature: string
  unit?: string
  threshold?: boolean
  events?: Row[]
  onSelect?: (row: Row) => void
}) {
  return (
    <div
      className="chart history-chart"
      role="img"
      aria-label={`${feature} historical series with ${events.length} filtered event markers`}
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
        initialDimension={{ width: 900, height: 320 }}
      >
        <LineChart data={rows} margin={{ top: 12, right: 15, bottom: 5, left: 12 }}>
          <CartesianGrid vertical={false} stroke="#e3e4dd" />
          <XAxis dataKey="date" minTickGap={70} tickLine={false} axisLine={false} />
          <YAxis
            domain={['auto', 'auto']}
            tickFormatter={(v) =>
              unit === 'percent' ? `${(v * 100).toFixed(1)}%` : Number(v).toFixed(1)
            }
            width={65}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip formatter={(v) => format(Number(v), unit)} />
          <Line
            dataKey={feature}
            name={feature.replaceAll('_', ' ')}
            stroke="#404d57"
            strokeWidth={1.6}
            dot={false}
            isAnimationActive={false}
            connectNulls={false}
          />
          {threshold && (
            <Line
              dataKey={`${feature}_threshold`}
              name="Prior 20th-percentile threshold"
              stroke="#ad9566"
              strokeDasharray="4 3"
              dot={false}
              isAnimationActive={false}
            />
          )}{' '}
          {events.map((row) => (
            <ReferenceDot
              key={String(row.date)}
              x={String(row.date)}
              y={Number(row[feature])}
              r={4}
              fill="#52745f"
              stroke="#f6f5f0"
              onClick={() => onSelect?.(row)}
              style={{ cursor: 'pointer' }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function Explorer({
  manifest,
  data,
  featureMode = false,
  query = '',
}: {
  manifest: Manifest
  data: Dashboard
  featureMode?: boolean
  query?: string
}) {
  const params = new URLSearchParams(query)
  const requestedExperiment = params.get('experiment') || 'EXP-002'
  const [experiment, setExperiment] = useState(requestedExperiment)
  const [ticker, setTicker] = useState(params.get('ticker') || '')
  const [series, setSeries] = useState<Series | null>(null)
  const [error, setError] = useState('')
  const [selectedDate, setSelectedDate] = useState(params.get('date') || '')
  const [featureKey, setFeatureKey] = useState('drawdown_60d')
  const [filters, setFilters] = useState<Filters>({
    start: '',
    end: '',
    components: 'all',
    kind: 'event',
    split: 'all',
  })
  const tickers = Object.keys(manifest.series)
    .filter((k) => k.startsWith(`${experiment}/`))
    .map((k) => k.split('/')[1])
  const currentTicker = tickers.includes(ticker) ? ticker : tickers[0] || ''
  useEffect(() => {
    const abort = new AbortController()
    setSeries(null)
    setError('')
    if (!currentTicker) {
      setError('No preserved ticker histories are available.')
      return
    }
    loadSeries(manifest, experiment, currentTicker, abort.signal)
      .then((s) => {
        setSeries(s)
        setFilters((f) => ({ ...f, start: '', end: '', split: 'all' }))
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message)
      })
    return () => abort.abort()
  }, [manifest, experiment, currentTicker])
  const filtered = useMemo(
    () => filterObservations(series?.known_at_signal || [], filters),
    [series, filters],
  )
  const context = useMemo(
    () =>
      filterObservations(series?.known_at_signal || [], {
        ...filters,
        kind: 'all',
        components: 'all',
      }),
    [series, filters],
  )
  const selected = filtered.find((r) => r.date === selectedDate) || filtered.at(-1)
  const decisionContext = selected
    ? context.filter((row) => String(row.date) <= String(selected.date))
    : []
  const feature = data.feature_catalog.find((f) => f.key === featureKey)!
  const update = (key: keyof Filters, value: string) => setFilters((f) => ({ ...f, [key]: value }))
  const future = selected ? series?.future_outcomes[String(selected.date)] : undefined
  return (
    <>
      <PageTitle
        eyebrow={featureMode ? 'Quantitative mechanics' : 'Historical signal inspection'}
        title={featureMode ? 'Feature explorer' : 'What was known when the signal fired?'}
      >
        {featureMode
          ? 'Definitions and historical series from the Python feature engine.'
          : 'Signal-time features are separate from future outcomes used for research evaluation.'}
      </PageTitle>
      <div className="filters">
        <label className="field">
          Experiment
          <select
            value={experiment}
            onChange={(e) => {
              setExperiment(e.target.value)
              setSelectedDate('')
            }}
          >
            <option>EXP-002</option>
            <option>EXP-001</option>
          </select>
        </label>
        <label className="field">
          Ticker
          <select
            value={currentTicker}
            onChange={(e) => {
              setTicker(e.target.value)
              setSelectedDate('')
            }}
          >
            {tickers.map((t) => (
              <option key={t}>{t}</option>
            ))}
          </select>
        </label>
        <label className="field">
          From
          <input
            type="date"
            value={filters.start}
            onChange={(e) => update('start', e.target.value)}
          />
        </label>
        <label className="field">
          Through
          <input type="date" value={filters.end} onChange={(e) => update('end', e.target.value)} />
        </label>
        <label className="field">
          Period
          <select value={filters.split} onChange={(e) => update('split', e.target.value)}>
            <option value="all">All available</option>
            {(experiment === 'EXP-001' ? ['research', 'validation', 'test'] : ['test']).map((s) => (
              <option key={s} value={s}>
                {s === 'test' && experiment === 'EXP-002' ? 'Historical OOS' : s}
              </option>
            ))}
          </select>
        </label>
        {!featureMode && (
          <>
            <label className="field">
              Observation
              <select value={filters.kind} onChange={(e) => update('kind', e.target.value)}>
                <option value="event">Events</option>
                <option value="condition">Condition days</option>
                <option value="all">All observations</option>
              </select>
            </label>
            <label className="field">
              Components
              <select
                value={filters.components}
                onChange={(e) => update('components', e.target.value)}
              >
                <option value="all">All</option>
                {[0, 1, 2, 3, 4].map((n) => (
                  <option key={n}>{n}</option>
                ))}
              </select>
            </label>
          </>
        )}
      </div>
      {error ? (
        <Empty title="History unavailable">{error}</Empty>
      ) : !series ? (
        <p role="status">Verifying selected ticker history…</p>
      ) : featureMode ? (
        <>
          <Section
            title={feature.group}
            note={`${currentTicker} · ${experiment} · historical adjusted vintage`}
          >
            <label className="field feature-select">
              Feature
              <select value={featureKey} onChange={(e) => setFeatureKey(e.target.value)}>
                {[...new Set(data.feature_catalog.map((f) => f.group))].map((group) => (
                  <optgroup key={group} label={group}>
                    {data.feature_catalog
                      .filter((f) => f.group === group)
                      .map((f) => (
                        <option key={f.key} value={f.key}>
                          {f.key}
                          {f.used_in_v1 ? ' · V1' : ''}
                        </option>
                      ))}
                  </optgroup>
                ))}
              </select>
            </label>
            <div className="feature-definition">
              <code>{feature.formula}</code>
              <p>{feature.interpretation}</p>
              <dl className="facts">
                <dt>Window</dt>
                <dd>{feature.window}</dd>
                <dt>Warm-up</dt>
                <dd>{feature.warmup}</dd>
                <dt>Input</dt>
                <dd>{feature.data}</dd>
                <dt>Availability</dt>
                <dd>{feature.availability}</dd>
                <dt>Used in frozen V1</dt>
                <dd>{feature.used_in_v1 ? 'Yes' : 'No'}</dd>
                <dt>Last displayed value</dt>
                <dd>
                  {format(context.at(-1)?.[feature.key], feature.unit)} ·{' '}
                  {String(context.at(-1)?.date || 'No rows')}
                </dd>
              </dl>
            </div>
            <History
              rows={context}
              feature={feature.key}
              unit={feature.unit}
              threshold={feature.used_in_v1}
            />
            <p className="footnote">
              Undefined warm-up or missing values remain gaps. Bars mean observed trading rows. The
              dashed threshold uses prior observations only.
            </p>
          </Section>
          <Section
            title="Feature catalog"
            note="Select any of the definitions above; all calculations remain in Python."
          >
            <DataTable
              rows={data.feature_catalog.map((f) => ({
                feature: f.key,
                group: f.group,
                window: f.window,
                v1: f.used_in_v1,
              }))}
              columns={[
                { key: 'feature', label: 'Feature' },
                { key: 'group', label: 'Family' },
                { key: 'window', label: 'Window' },
                { key: 'v1', label: 'V1' },
              ]}
              caption="Feature definitions"
              onSelect={(r) => setFeatureKey(String(r.feature))}
              pageSize={30}
            />
          </Section>
        </>
      ) : (
        <>
          <Section
            title={`${currentTicker} · adjusted close`}
            note={`${context.length.toLocaleString()} observations · ${filtered.length.toLocaleString()} matching rows · ${series.availability}`}
          >
            <History
              rows={context}
              feature="close"
              events={filtered.filter((r) => r.dip_event_v1)}
              onSelect={(r) => setSelectedDate(String(r.date))}
            />
            <p className="footnote">
              Green markers identify filtered events. Select a marker or table date; the line
              retains intervening prices.
            </p>
            <DataTable
              rows={[...filtered].reverse()}
              columns={[
                { key: 'date', label: 'Signal session' },
                { key: 'fold', label: 'Period / fold' },
                { key: 'close', label: 'Adjusted close', format: 'price' },
                { key: 'dip_ready_v1', label: 'Ready' },
                { key: 'dip_condition_v1', label: 'Condition' },
                { key: 'dip_event_v1', label: 'Event' },
                { key: 'dip_component_count', label: 'Components', format: 'integer' },
              ]}
              caption="Filtered historical signal observations"
              onSelect={(r) => setSelectedDate(String(r.date))}
              pageSize={8}
            />
          </Section>
          {selected ? (
            <>
              <div className="decision-section">
                <span className="eyebrow">
                  Information known at signal time · after session close
                </span>
                <h2>
                  {currentTicker} / {String(selected.date)}
                </h2>
                <p>
                  Components {String(selected.dip_component_count)} of 4 · Ready{' '}
                  {String(selected.dip_ready_v1)} · Condition {String(selected.dip_condition_v1)} ·
                  Event {String(selected.dip_event_v1)}
                </p>
                <Anatomy row={selected} />
                <label className="field feature-select">
                  Inspect component threshold
                  <select value={featureKey} onChange={(e) => setFeatureKey(e.target.value)}>
                    {componentKeys.map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <History
                  rows={decisionContext}
                  feature={featureKey}
                  unit={featureKey === 'price_zscore_20d' ? 'number' : 'percent'}
                  threshold
                />
                <div
                  className="chart"
                  style={{ height: 150 }}
                  role="img"
                  aria-label="Component activation timeline; stacked active components"
                >
                  <ResponsiveContainer initialDimension={{ width: 900, height: 150 }}>
                    <BarChart data={decisionContext}>
                      <XAxis dataKey="date" minTickGap={90} />
                      <YAxis domain={[0, 4]} ticks={[0, 1, 2, 3, 4]} />
                      <Tooltip />
                      <Legend iconType="square" />
                      {componentKeys.map(([, label, active], i) => (
                        <Bar
                          key={active}
                          dataKey={(row: Row) => (row.dip_ready_v1 ? (row[active] ? 1 : 0) : null)}
                          name={label}
                          stackId="components"
                          fill={['#52745f', '#87977a', '#b3bca5', '#b7a078'][i]}
                          isAnimationActive={false}
                        />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <p className="footnote">
                  Charts in this panel stop at the selected signal session; later observations are
                  excluded.
                </p>
              </div>
              <div className="outcome-section">
                <span className="eyebrow">Future outcome · research evaluation only</span>
                <h2>What happened after this decision?</h2>
                <p>
                  These values were unavailable at signal time. Entry is the next observed session
                  open; split/fold censoring remains intact.
                </p>
                {future ? (
                  <>
                    <DataTable
                      rows={future.horizons || []}
                      columns={[
                        { key: 'horizon', label: 'Bars' },
                        { key: 'status', label: 'Outcome status' },
                        {
                          key: 'entry_timestamp',
                          label: 'Entry session',
                          render: (r) => String(r.entry_timestamp || '—').slice(0, 10),
                        },
                        { key: 'entry_price', label: 'Entry open', format: 'price' },
                        { key: 'forward_return', label: 'Gross return', format: 'percent' },
                        { key: 'benchmark_return', label: 'SPY', format: 'percent' },
                        { key: 'mfe', label: 'MFE', format: 'percent' },
                        { key: 'mae', label: 'MAE', format: 'percent' },
                      ]}
                      caption="Future fixed-horizon outcomes"
                    />
                    <DataTable
                      rows={future.trades || []}
                      columns={[
                        { key: 'mode', label: 'Trade mode' },
                        { key: 'status', label: 'Status' },
                        { key: 'exit_reason', label: 'Exit' },
                        { key: 'holding_bars', label: 'Bars', format: 'integer' },
                        { key: 'net_return', label: 'Net return', format: 'percent' },
                        {
                          key: 'exit_timestamp',
                          label: 'Exit session',
                          render: (r) => String(r.exit_timestamp || '—').slice(0, 10),
                        },
                      ]}
                      caption="Future barrier outcomes"
                    />
                  </>
                ) : (
                  <Note>
                    No event outcome was evaluated for this observation. Condition days and
                    non-events do not acquire invented trade outcomes.
                  </Note>
                )}
              </div>
            </>
          ) : (
            <Empty title="No matching observations">
              Adjust the filters to inspect the preserved history.
            </Empty>
          )}
        </>
      )}
      <Note>
        Historical adjusted data can include later corporate actions and revisions. Causal
        calculations on this vintage do not establish that these exact values were available
        historically. Neither historical sample is a fresh temporal holdout.
      </Note>
    </>
  )
}
