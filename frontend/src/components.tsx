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
    'Arithmetic average of the observed return fractions. Large observations can influence it.',
  'Median return': 'Middle observed return; half of returns lie on either side.',
  Expectancy:
    'Mean net return per completed trade, including zero returns. Not an annualized portfolio return.',
  'Win rate': 'Fraction of completed observations with return strictly greater than zero.',
  'Profit factor':
    'Sum of positive returns divided by the absolute sum of negative returns. Undefined if there are no losses.',
  MFE: 'Maximum favorable excursion: highest observed high / entry open − 1 over the measured window.',
  MAE: 'Maximum adverse excursion: lowest observed low / entry open − 1. Negative values represent adverse moves.',
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
}
export function Help({ name, children }: { name: string; children?: ReactNode }) {
  return (
    <abbr tabIndex={0} title={glossary[name] || name}>
      {children || name}
    </abbr>
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
  { key: 'win_rate', label: 'Win rate', format: 'percent' },
  { key: 'profit_factor', label: 'Profit factor', format: 'number' },
]
