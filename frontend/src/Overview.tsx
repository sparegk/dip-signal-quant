import { type Dashboard, type Exp2, format } from './data'
import {
  Bars,
  ComparisonChart,
  DataTable,
  Empty,
  foldColumns,
  comparisonColumns,
  Metric,
  Note,
  PageTitle,
  Section,
} from './components'

export function Evidence({ research }: { research: Exp2 }) {
  return (
    <Section
      title="Does it have an edge?"
      note="Observed historical separation · gross event returns · pooled historical OOS"
    >
      <ComparisonChart rows={research.comparison} />
      <DataTable
        rows={research.comparison}
        columns={comparisonColumns}
        caption="Event and baseline forward-return comparison"
      />
      <p className="footnote">
        Δ denotes percentage-point differences. Stock controls may have different ticker/date
        composition; SPY differences use paired observations. Event-mean intervals do not establish
        significance of baseline differences.
      </p>
    </Section>
  )
}
export default function Overview({ data }: { data: Dashboard }) {
  const research = data.exp002
  if (research.status !== 'available')
    return (
      <>
        <PageTitle eyebrow="Research status" title="DipSignal V1">
          Frozen equity dip / mean-reversion research.
        </PageTitle>
        <Empty title="Research artifacts unavailable">
          {research.reason} Export your preserved inputs to populate the historical evidence views.
        </Empty>
      </>
    )
  const ten = research.comparison.find((row) => row.horizon === 10)!
  const trade = research.tables.trade_oos_summary.find((row) => row.mode === 'non_overlapping')!
  return (
    <>
      <PageTitle eyebrow="Research overview / EXP-002" title="DipSignal V1">
        Quantitative equity dip / mean-reversion research. A fixed hypothesis, evaluated against
        simple baselines.
      </PageTitle>
      <div className="status-line">
        <span className="tag">V1 frozen</span>
        {data.experiments.map((e) => (
          <span key={e.id}>{e.id} complete</span>
        ))}
        <span>Manual archive initialized</span>
        <span>Live trading not enabled</span>
      </div>
      <Note warning>
        <strong>
          Registered breadth criterion: {research.criteria.breadth_passed ? 'passed' : 'failed'}.
        </strong>{' '}
        {research.criteria.positive_excess_tickers}/{research.criteria.defined_tickers} tickers have
        positive ten-bar matched-SPY excess. Positive pooled results do not establish broad
        incremental value.
      </Note>
      <div className="scope-line">
        <strong>
          Historical OOS · {research.folds[0]?.test_start as string} →{' '}
          {research.folds.at(-1)?.test_end as string}
        </strong>
        <span>
          {research.metadata.usable_count} usable / {research.metadata.requested_count} requested ·
          static current constituents · consumed sample
        </span>
      </div>
      <div className="metric-grid">
        <Metric label="Mean return" value={ten.mean} note="10-bar event · gross · historical OOS" />
        <Metric
          label="Matched-SPY excess"
          value={ten.difference_spy}
          kind="pp"
          note={`10-bar paired SPY ${format(ten.benchmark_mean)}`}
        />
        <Metric
          label="Expectancy"
          value={trade.average_return}
          note="Non-overlapping trade · net · historical OOS"
        />
        <Metric
          label="Win rate"
          value={trade.win_rate}
          note="Completed non-overlapping trades · net"
        />
        <Metric
          label="Profit factor"
          value={trade.profit_factor}
          kind="number"
          note="Equal-notional trades · not portfolio P&L"
        />
        <Metric
          label="Median return"
          value={trade.median_return}
          note="Non-overlapping trade · net · historical OOS"
        />
      </div>
      <div className="secondary-metrics">
        <span>
          Event MFE <strong>{format(ten.average_mfe)}</strong>
        </span>
        <span>
          Event MAE <strong className="negative">{format(ten.average_mae)}</strong>
        </span>
        <span>
          Events <strong>{format(research.frequency.events, 'integer')}</strong>
        </span>
        <span>
          Per 252 ready bars{' '}
          <strong>{format(research.frequency.events_per_252_ready, 'number')}</strong>
        </span>
      </div>
      <Evidence research={research} />
      <Section
        title="Across time, the result is uneven"
        note="Annual expanding-history folds · non-overlapping trades after costs"
        action={<a href="#robustness">Inspect robustness →</a>}
      >
        <div className="two-column">
          <Bars rows={research.folds} x="fold" y="net_mean" label="Mean net trade return" />
          <div className="reading-note">
            <span className="eyebrow">Keep the negative evidence</span>
            <h3>One average is not the whole result.</h3>
            <p>
              The losing fold stays in the analysis. Shorter horizons, individual stocks and market
              contexts can behave differently.
            </p>
            <p>
              2026 is a partial historical fold through {String(research.folds.at(-1)?.test_end)},
              not a live YTD result.
            </p>
          </div>
        </div>
        <DataTable
          rows={research.folds}
          columns={foldColumns}
          caption="Annual walk-forward evidence"
        />
      </Section>
      <Section
        title="Prospective evidence"
        note="A separate sample, preserved before its intended execution opportunity"
      >
        <p>
          {data.archive.prospective_count === 0
            ? 'Prospective archive initialized — awaiting first eligible completed session.'
            : `${data.archive.prospective_count} genuinely prospective records preserved.`}
        </p>
        <p className="footnote">
          Collection is manually invoked, not continuously active. No prospective outcome evaluation
          is implemented. First review is no earlier than {data.archive.config.review_dates[0]},
          subject to the registered coverage gate and separate authorization.
        </p>
        <a href="#paper-archive">Inspect the paper archive →</a>
      </Section>
      <Note>
        Descriptive historical evidence; statistical significance and future profitability are not
        established. Current constituents retain survivorship bias. Both historical experiment
        samples have been consumed.
      </Note>
    </>
  )
}
