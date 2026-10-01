import { useState, type ReactNode } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { format, tone, type Row } from './data'

export const glossary: Record<string, string> = {
  'Mean return':
    'Add the returns and divide by the number of observations. A few large wins can lift the average.',
  'Median return': 'Middle observed return; half of returns lie on either side.',
  Expectancy:
    'Average return per completed trade after costs, including flat trades. It describes this sample.',
  'Win rate': 'The share of completed trades or observations that made a positive return.',
  'Profit factor':
    'Total positive returns divided by total losses as a positive number. Above 1 means gains exceeded losses. Undefined with no losses.',
  MFE: 'The biggest rise above the entry price within the measured window. This is an opportunity seen afterward, not a realized gain.',
  MAE: 'The deepest fall below the entry price within the measured window. This shows the adverse move along the way.',
  Sharpe:
    'Mean excess periodic capital return / its standard deviation, annualized. Not defined for these pooled event ledgers.',
  Sortino:
    'Mean return above a target / downside deviation, annualized. Requires a defined periodic capital series.',
  Drawdown:
    'Decline from a prior peak. The V1 feature uses the trailing highest close, not portfolio equity.',
  'Matched-SPY excess':
    'Stock event return minus SPY return over the same entry and endpoint dates; paired rows only.',
  'Walk-forward':
    'Chronological evaluation windows with expanding prior history. Frozen V1 has no fitted model.',
  'Survivorship bias':
    'Selecting stocks that survive today can omit historical failures and change the observed evidence.',
  'Look-ahead bias':
    'Using information that was unavailable when a historical decision would have been made.',
  'Cross-sectional robustness':
    'Whether behavior extends across stocks rather than being concentrated in a few names.',
  'Gross / net': 'Gross is before trading costs. Net is after the assumed commission and slippage.',
  'Historical OOS':
    'Historical periods evaluated under previously fixed rules. They have now been inspected, so they are not a fresh future test.',
  Baseline:
    'A simple comparison, such as ordinary stock days or SPY over the same dates. A positive return alone is not enough.',
  'Statistical significance':
    'Whether the observed difference is hard to explain by chance under a stated model. These baseline differences have not passed such a test.',
  'Basis point': 'One basis point (bp) is 0.01 percentage point. Ten basis points is 0.10%.',
  'Trading bar':
    'One observed market session in this project. Ten bars means ten observed trading sessions, not ten calendar days.',
}
export function Help({ name, children }: { name: string; children?: ReactNode }) {
  const [open, setOpen] = useState(false)
  if (!glossary[name]) return <span>{children || name}</span>
  return (
    <span className="metric-help">
      <button
        type="button"
        aria-expanded={open}
        aria-label={`Explain ${name}`}
        onClick={() => setOpen(!open)}
      >
        {children || name} <span aria-hidden="true">?</span>
      </button>
      {open && (
        <span className="help-explanation" role="note">
          {glossary[name]}
          {examples[name] && <span className="help-example">Example only: {examples[name]}</span>}
        </span>
      )}
    </span>
  )
}
export const examples: Record<string, string> = {
  'Mean return': 'Returns of +4%, +1%, −2% average +1%. A few large wins can lift this number.',
  'Median return': 'For −2%, +1%, +12%, the median is +1%, even though the average is higher.',
  Expectancy:
    'If equal-size completed trades average +0.5% after costs, that is the sample expectancy—not a promise for the next trade.',
  'Win rate':
    '6 profitable trades out of 10 gives 60%. Large losses can still make the overall result negative.',
  'Profit factor':
    'With equal-size trades, gains totaling 12% and losses totaling 10% give 1.2. This is not a 20% portfolio return.',
  MFE: 'Entry at $100; highest price in the window $106: MFE = +6%. It does not mean you sold there.',
  MAE: 'Entry at $100; lowest price in the window $93: MAE = −7%. It does not mean you sold there.',
  'Matched-SPY excess': 'Stock +3%, SPY +2% over the same dates: excess = +1 percentage point.',
  Drawdown: 'A price falls from a recent $100 high to $90: drawdown = −10%.',
  'Walk-forward':
    'Use history through 2021 to evaluate 2022, then history through 2022 to evaluate 2023.',
  'Survivorship bias': 'Testing only companies that exist today can leave out earlier failures.',
  'Look-ahead bias':
    'Using tomorrow’s closing price to choose today’s signal would leak future information.',
  'Cross-sectional robustness':
    'Ask whether the result appears across many stocks, not just the best two.',
}
export function Disclosure({ title, children }: { title: string; children: ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <details className="disclosure" onToggle={(event) => setOpen(event.currentTarget.open)}>
      <summary>{title}</summary>
      {open && <div className="disclosure-content">{children}</div>}
    </details>
  )
}
export function PageTitle({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string
  title: string
  children?: ReactNode
}) {
  return (
    <header className="page-title">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      {children && <p>{children}</p>}
    </header>
  )
}
export function Section({
  title,
  note,
  children,
  action,
}: {
  title: string
  note?: string
  children: ReactNode
  action?: ReactNode
}) {
  return (
    <section className="section">
      <div className="section-heading">
        <div>
          <h2>{title}</h2>
          {note && <p>{note}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}
export function Note({ children, warning = false }: { children: ReactNode; warning?: boolean }) {
  return <div className={warning ? 'note warning' : 'note'}>{children}</div>
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <h2>{title}</h2>
      <p>{children}</p>
    </div>
  )
}
export function Metric({
  label,
  value,
  kind = 'percent',
  note,
}: {
  label: string
  value: unknown
  kind?: string
  note: string
}) {
  return (
    <div className="metric">
      <div className="metric-label">
        <Help name={label} />
      </div>
      <strong className={kind === 'percent' || kind === 'pp' ? tone(value) : ''}>
        {format(value, kind)}
      </strong>
      <span>{note}</span>
    </div>
  )
}
export type Column = {
  key: string
  label: string
  format?: string
  render?: (row: Row) => ReactNode
}
export function DataTable({
  rows,
  columns,
  caption,
  pageSize = 15,
  onSelect,
}: {
  rows: Row[]
  columns: Column[]
  caption: string
  pageSize?: number
  onSelect?: (row: Row) => void
}) {
  const [sort, setSort] = useState<{ key: string; direction: number } | null>(null)
  const [page, setPage] = useState(0)
  const ordered = sort
    ? [...rows].sort((a, b) => {
        const x = a[sort.key],
          y = b[sort.key]
        if (x === null || x === undefined) return 1
        if (y === null || y === undefined) return -1
        return (
          sort.direction *
          (typeof x === 'number' && typeof y === 'number'
            ? x - y
            : String(x).localeCompare(String(y)))
        )
      })
    : rows
  const lastPage = Math.max(0, Math.ceil(rows.length / pageSize) - 1)
  const currentPage = Math.min(page, lastPage)
  return (
    <>
      <div className="table-scroll">
        <table>
          <caption className="sr-only">{caption}</caption>
          <thead>
            <tr>
              {columns.map((col) => (
                <th
                  key={col.key}
                  scope="col"
                  aria-sort={
                    sort?.key === col.key
                      ? sort.direction === 1
                        ? 'ascending'
                        : 'descending'
                      : 'none'
                  }
                >
                  <button
                    title={glossary[col.label]}
                    onClick={() => {
                      setSort({
                        key: col.key,
                        direction: sort?.key === col.key ? -sort.direction : 1,
                      })
                      setPage(0)
                    }}
                  >
                    {col.label}
                    {sort?.key === col.key ? (sort.direction === 1 ? ' ↑' : ' ↓') : ''}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ordered.slice(currentPage * pageSize, (currentPage + 1) * pageSize).map((row, i) => (
              <tr key={String(row.record_id || row.ticker || row.date || '') + i}>
                {columns.map((col, j) => (
                  <td
                    key={col.key}
                    className={
                      col.format
                        ? `numeric ${col.format === 'percent' || col.format === 'pp' ? tone(row[col.key]) : ''}`
                        : ''
                    }
                  >
                    {onSelect && j === 0 ? (
                      <button className="text-button" onClick={() => onSelect(row)}>
                        {String(row[col.key] ?? '—')}
                      </button>
                    ) : col.render ? (
                      col.render(row)
                    ) : col.format ? (
                      format(row[col.key], col.format)
                    ) : (
                      String(row[col.key] ?? '—')
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="table-empty">No observations match these filters.</p>}
      </div>
      {rows.length > pageSize && (
        <div className="pagination">
          <span>
            {currentPage * pageSize + 1}–{Math.min((currentPage + 1) * pageSize, rows.length)} of{' '}
            {rows.length.toLocaleString()}
          </span>
          <button disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>
            Previous
          </button>
          <button disabled={currentPage >= lastPage} onClick={() => setPage(currentPage + 1)}>
            Next
          </button>
        </div>
      )}
    </>
  )
}
const colors = ['#376953', '#777c75', '#b49b68', '#404d57']
export function ComparisonChart({ rows }: { rows: Row[] }) {
  return (
    <div
      className="chart"
      role="img"
      aria-label="Gross event and baseline mean returns by forward horizon"
    >
      <ResponsiveContainer
        width="100%"
        height="100%"
        initialDimension={{ width: 600, height: 280 }}
      >
        <LineChart data={rows} margin={{ top: 12, right: 18, bottom: 8, left: 10 }}>
          <CartesianGrid vertical={false} stroke="#e3e4dd" />
          <XAxis
            dataKey="horizon"
            tickFormatter={(x) => `${x} bars`}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tickFormatter={(x) => `${(x * 100).toFixed(1)}%`}
            tickLine={false}
            axisLine={false}
            width={52}
          />
          <Tooltip
            formatter={(v) => format(Number(v))}
            labelFormatter={(x) => `${x}-bar horizon`}
          />
          <Legend iconType="plainline" />
          {[
            ['mean', 'DipSignal event'],
            ['unconditional', 'Unconditional'],
            ['non_signal', 'Non-signal'],
            ['benchmark_mean', 'Matched SPY'],
          ].map(([key, name], i) => (
            <Line
              key={key}
              dataKey={key}
              name={name}
              stroke={colors[i]}
              strokeWidth={key === 'mean' ? 2.5 : 1.5}
              strokeDasharray={i === 2 ? '4 3' : undefined}
              dot={{ r: 3 }}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
export function Bars({
  rows,
  x,
  y,
  label,
  percent = true,
  height = 230,
}: {
  rows: Row[]
  x: string
  y: string
  label: string
  percent?: boolean
  height?: number
}) {
  return (
    <div className="chart" style={{ height }} role="img" aria-label={label}>
      <ResponsiveContainer width="100%" height="100%" initialDimension={{ width: 600, height }}>
        <BarChart data={rows} margin={{ top: 8, right: 12, bottom: 10, left: 8 }}>
          <CartesianGrid vertical={false} stroke="#e3e4dd" />
          <XAxis
            dataKey={x}
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) =>
              typeof v === 'number' && x === 'center' ? `${(v * 100).toFixed(1)}%` : String(v)
            }
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tickFormatter={(v) => (percent ? `${(v * 100).toFixed(1)}%` : String(v))}
            width={55}
          />
          <Tooltip
            formatter={(v) => format(Number(v), percent ? 'percent' : 'integer')}
            labelFormatter={(v) => (x === 'center' ? `Bin center ${format(Number(v))}` : String(v))}
          />
          <ReferenceLine y={0} stroke="#a5a99f" />
          <Bar dataKey={y} name={label} maxBarSize={45} isAnimationActive={false}>
            {rows.map((row, i) => (
              <Cell
                key={i}
                fill={Number(row[x === 'center' ? 'center' : y]) < 0 ? '#a2594d' : '#52745f'}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
export const comparisonColumns: Column[] = [
  { key: 'horizon', label: 'Bars' },
  { key: 'count', label: 'Complete N', format: 'integer' },
  { key: 'mean', label: 'Event', format: 'percent' },
  { key: 'unconditional', label: 'Unconditional', format: 'percent' },
  { key: 'non_signal', label: 'Non-signal', format: 'percent' },
  { key: 'benchmark_mean', label: 'Matched SPY', format: 'percent' },
  { key: 'difference_unconditional', label: 'Δ unconditional', format: 'pp' },
  { key: 'difference_non_signal', label: 'Δ non-signal', format: 'pp' },
  { key: 'difference_spy', label: 'Paired Δ SPY', format: 'pp' },
]
export const foldColumns: Column[] = [
  { key: 'fold', label: 'OOS fold' },
  { key: 'events', label: 'Events', format: 'integer' },
  { key: 'event_mean', label: '10-bar gross', format: 'percent' },
  { key: 'net_mean', label: 'Trade net', format: 'percent' },
  { key: 'spy_excess', label: 'Paired Δ SPY', format: 'pp' },
  { key: 'win_rate', label: 'Win rate', format: 'rate' },
  { key: 'profit_factor', label: 'Profit factor', format: 'number' },
]
