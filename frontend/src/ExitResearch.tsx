import { useState } from 'react'
import { Bars, DataTable, Disclosure, Note, PageTitle, Section, type Column } from './components'
import { format, tone, type Dashboard, type Row } from './data'
import { Missing } from './Research'

export const policyNames: Record<string, string> = {
  v1_control: 'V1 fixed exit',
  training_selected: 'Training-selected adaptive',
  time_only: 'Hold for 10 bars',
  target_only: 'Target only',
  stop_only: 'Stop only',
  best_fixed: 'Training-selected fixed',
  best_atr: 'Training-selected ATR',
  best_r_multiple: 'Training-selected ATR / R',
}
const primary = ['v1_control', 'training_selected', 'time_only']
export const exitColumns: Column[] = [
  { key: 'label', label: 'Exit policy' },
  { key: 'trade_count', label: 'Trades', format: 'integer' },
  { key: 'expected_value', label: 'Net EV', format: 'percent' },
  { key: 'expected_dollars_per_1000', label: 'Mean $ / $1,000 trade', format: 'price' },
  { key: 'median_return', label: 'Median return', format: 'percent' },
  { key: 'win_rate', label: 'Win rate', format: 'rate' },
  { key: 'profit_factor', label: 'Profit factor', format: 'number' },
  { key: 'average_win', label: 'Average win', format: 'percent' },
  { key: 'average_loss', label: 'Average loss', format: 'percent' },
  { key: 'fifth_percentile_net', label: 'Worst 5% cutoff', format: 'percent' },
]
const labels = (rows: Row[]): Row[] =>
  rows.map((r) => ({ ...r, label: policyNames[String(r.policy)] || r.policy }))

export default function ExitResearch({ data }: { data: Dashboard }) {
  const [mode, setMode] = useState('independent')
  const e = data.exp004
  if (!e || e.status !== 'available' || !e.tables) return <Missing reason={e?.reason} />
  const rows = labels(e.tables.aggregate_summary.filter((r) => r.mode === mode))
  const main = primary.map((p) => rows.find((r) => r.policy === p)).filter((r): r is Row => !!r)
  const folds = e.tables.fold_summary.filter(
    (r) => r.mode === mode && primary.includes(String(r.policy)),
  )
  const years = [...new Set(folds.map((r) => String(r.fold)))].sort()
  const efficiency = labels(
    e.tables.exit_efficiency.filter(
      (r) => r.fold === 'ALL' && r.mode === mode && primary.includes(String(r.policy)),
    ),
  )
  return (
    <>
      <PageTitle eyebrow="EXP-004 · Consumed historical fold-OOS" title="How Should We Exit a Dip?">
        Same signal. Same entry. Different exit behavior.
      </PageTitle>
      <Note warning>
        <strong>Historical finding.</strong> Adaptive exits beat V1's net EV in this sample, but
        holding for 10 bars had higher average EV. Adaptive exits allowed larger losses than V1. A
        validated improvement has not been established.
      </Note>
      <div className="filters">
        <label>
          Analysis mode
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="independent">Same-entry independent events</option>
            <option value="non_overlapping">Non-overlapping trades</option>
          </select>
        </label>
      </div>
      <p className="small">
        Net after 1 bp commission + 5 bp slippage per side · 2021–2026 partial ·{' '}
        {mode === 'independent'
          ? 'Overlapping events share the same entries.'
          : 'Exit-dependent occupancy means policies accept different subsets.'}{' '}
        These are trade statistics, not portfolio returns.
      </p>
      <Section
        title="Profit and risk together"
        note="EV means average net profit per trade. A higher win rate can still hide larger losses."
      >
        <DataTable
          rows={main}
          columns={exitColumns}
          caption="Fixed adaptive and time-only comparison"
        />
        <Bars
          rows={main}
          x="label"
          y="expected_value"
          label="Mean net return per completed trade"
        />
        <Disclosure title="How expected value is built">
          <p>
            EV = win probability × average win + loss probability × average loss. Flat trades stay
            in the denominator. Average losses are negative.
          </p>
          <DataTable
            rows={main}
            columns={[
              { key: 'label', label: 'Policy' },
              { key: 'win_probability', label: 'Win probability', format: 'rate' },
              { key: 'loss_probability', label: 'Loss probability', format: 'rate' },
              { key: 'average_win', label: 'Average win', format: 'percent' },
              { key: 'average_loss', label: 'Average loss', format: 'percent' },
              { key: 'expected_value', label: 'Net EV', format: 'percent' },
            ]}
            caption="EV decomposition"
          />
          <p className="small">
            For an equal-notional $1,000 trade, 1% is $10. This scale illustration does not assume a
            portfolio allocation.
          </p>
        </Disclosure>
      </Section>
      <Section
        title="Every year, including the difficult ones"
        note="2026 is partial. Green and red show observed net EV, not confidence."
      >
        <div className="table-scroll">
          <table>
            <caption className="sr-only">Yearly net EV heatmap</caption>
            <thead>
              <tr>
                <th>Policy</th>
                {years.map((y) => (
                  <th key={y}>{y}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {primary.map((p) => (
                <tr key={p}>
                  <th>{policyNames[p]}</th>
                  {years.map((y) => {
                    const r = folds.find((r) => r.policy === p && String(r.fold) === y)
                    return (
                      <td key={y} className={`numeric ${tone(r?.expected_value)}`}>
                        {format(r?.expected_value)}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <Disclosure title="Yearly win rate, median and downside">
          <DataTable
            rows={labels(folds)}
            columns={[{ key: 'fold', label: 'Year' }, ...exitColumns]}
            caption="Annual exit comparisons"
            pageSize={18}
          />
        </Disclosure>
      </Section>
      <Section
        title="How much rebound did exits capture?"
        note="MFE is the highest opportunity seen afterward. It is not a price we could reliably sell at."
      >
        <DataTable
          rows={main}
          columns={[
            { key: 'label', label: 'Policy' },
            { key: 'expected_value', label: 'Realized net EV', format: 'percent' },
            { key: 'average_mfe', label: 'MFE until exit', format: 'percent' },
            { key: 'average_mae', label: 'MAE until exit', format: 'percent' },
            { key: 'average_holding_bars', label: 'Mean bars held', format: 'number' },
          ]}
          caption="Realized returns and path excursions"
        />
        <Disclosure title="Full-window capture and post-stop recovery">
          <DataTable
            rows={efficiency}
            columns={[
              { key: 'label', label: 'Policy' },
              { key: 'mean_full_window_mfe', label: 'Full 10-bar MFE', format: 'percent' },
              { key: 'mean_full_window_mae', label: 'Full 10-bar MAE', format: 'percent' },
              { key: 'median_capture', label: 'Median signed capture', format: 'number' },
              { key: 'mean_capture', label: 'Mean signed capture', format: 'number' },
              { key: 'mean_remaining_mfe', label: 'MFE after exit', format: 'percent' },
              { key: 'stopped_count', label: 'Stops', format: 'integer' },
              ...[2, 5, 10].map((n) => ({
                key: `recovery_${n}pct_rate`,
                label: `Entry +${n}% after stop`,
                render: (r: Row) =>
                  `${r[`recovery_${n}pct_count`] ?? '—'}/${r[`recovery_${n}pct_measurable_stops`] ?? '—'} (${format(r[`recovery_${n}pct_rate`], 'rate')})`,
              })),
            ]}
            caption="Exit capture and recovery diagnostics"
          />
          <p className="small">
            Capture = realized gross return / full-window MFE. Zero MFE is undefined; near-zero MFE
            can make mean ratios extremely negative. Post-stop recovery uses later highs relative to
            original entry, within the original ten bars. Different stop cohorts prevent causal
            comparisons.
          </p>
        </Disclosure>
      </Section>
      <Disclosure title="Exit counts, drawdowns and all controls">
        <DataTable
          rows={rows}
          columns={[
            ...exitColumns,
            { key: 'average_holding_bars', label: 'Bars', format: 'number' },
            { key: 'take_profit_count', label: 'TP', format: 'integer' },
            { key: 'stop_loss_count', label: 'SL', format: 'integer' },
            { key: 'time_exit_count', label: 'Time exits', format: 'integer' },
            { key: 'expectancy_r', label: 'EV / initial stop risk', format: 'number' },
            {
              key: 'worst_ticker_trade_close_drawdown',
              label: 'Worst ticker trade-close drawdown',
              format: 'percent',
            },
          ]}
          caption="All registered policies"
        />
        <p className="small">
          Drawdown is the worst individual ticker's non-overlapping trade-close compounded decline;
          pooled portfolio drawdown is undefined. No-stop controls have undefined R.
        </p>
      </Disclosure>
      <Section title="Edge scorecard" note="Separate measures, not a single strategy score.">
        <Scorecard data={data} mode={mode} />
      </Section>
      <Disclosure title="Training choices and stability">
        <DataTable
          rows={e.tables.selected_policy_by_fold.filter((r) => r.policy === 'training_selected')}
          columns={[
            { key: 'fold', label: 'Year' },
            { key: 'candidate_id', label: 'Frozen choice' },
            { key: 'training_trades', label: 'Training trades', format: 'integer' },
            { key: 'training_net_ev', label: 'Training EV', format: 'percent' },
          ]}
          caption="Training-selected configuration by fold"
        />
        <p>
          No fold-OOS outcome chose its own parameters. Historical periods are consumed, and 132
          selectable candidates create multiple-testing risk.
        </p>
      </Disclosure>
      <Note>Prospective evaluation pending genuine paper-signal outcomes.</Note>
    </>
  )
}

function Scorecard({ data, mode }: { data: Dashboard; mode: string }) {
  const rows = (data.exp004?.tables?.scorecard || []).filter((r) => r.mode === mode)
  const display = (value: unknown, kind: unknown) =>
    kind === 'text' ? String(value ?? '—') : format(value, String(kind))
  return (
    <DataTable
      rows={rows}
      columns={[
        { key: 'metric', label: 'Metric' },
        ...primary.map((p) => ({
          key: p,
          label: policyNames[p],
          render: (r: Row) => <span className="numeric">{display(r[p], r.kind)}</span>,
        })),
        {
          key: 'difference',
          label: 'Adaptive minus V1',
          render: (r) =>
            display(r.difference, r.kind === 'percent' || r.kind === 'rate' ? 'pp' : r.kind),
        },
        { key: 'status', label: 'Evidence status' },
      ]}
      caption="Separate evidence scorecard"
      pageSize={20}
    />
  )
}
