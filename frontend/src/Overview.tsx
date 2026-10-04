import { type Dashboard, type Exp2, format } from './data'
import {
  Bars,
  ComparisonChart,
  DataTable,
  Empty,
  foldColumns,
  comparisonColumns,
  Metric,
  Disclosure,
  Help,
  Note,
  PageTitle,
  Section,
} from './components'

export function Evidence({ research }: { research: Exp2 }) {
  return (
    <Section
      title="Does it have an edge?"
      note="Average return after each signal, before costs. Compare it with ordinary stock days and SPY."
    >
      <ComparisonChart rows={research.comparison} />
      <p className="chart-reading">
        Higher means a larger historical return. The green line is the signal; the other lines are
        comparisons. A gap alone does not prove an edge.
      </p>
      <Disclosure title="Exact returns and baseline differences">
        <DataTable
          rows={research.comparison}
          columns={comparisonColumns}
          caption="Event and baseline forward-return comparison"
        />
        <p className="footnote">
          Δ denotes percentage-point differences. Stock controls may have different ticker/date
          composition; SPY differences use paired observations. Event-mean intervals do not
          establish significance of baseline differences.
        </p>
      </Disclosure>
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
      {data.exp004?.status === 'available' && (
        <Note warning>
          <strong>Exit research:</strong> adaptive exits improved historical EV versus V1, but
          ten-bar holding averaged more and adaptive losses were larger.{' '}
          <a href="#exit-research">Compare profit and risk →</a>
        </Note>
      )}
      <PageTitle eyebrow="Research overview / EXP-002" title="DipSignal V1">
        Can unusually weak stocks bounce? Here is what the research shows so far.
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
        Only {research.criteria.positive_excess_tickers}/{research.criteria.defined_tickers} stocks
        beat SPY on average over the matched ten-bar windows. A majority was required.
      </Note>
      <div className="learning-path" aria-label="Start learning">
        <span className="eyebrow">New here? Start with three questions</span>
        <ol>
          <li>
            <a href="#signal-explorer">
              <span>01</span>Why did a signal fire?
            </a>
          </li>
          <li>
            <a href="#experiments">
              <span>02</span>Did it beat a simple comparison?
            </a>
          </li>
          <li>
            <a href="#robustness">
              <span>03</span>Did it repeat across stocks and years?
            </a>
          </li>
        </ol>
      </div>
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
      </div>
      <p className="reading-boundary">
        Gross = before costs. Net = after costs. An event is one signal; a trade adds entry and exit
        rules. Click a metric name for an example.
      </p>
      <Disclosure title="More metrics and what they mean">
        <div className="metric-grid brief-metrics">
          <Metric
            label="Win rate"
            value={trade.win_rate}
            kind="rate"
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
        <div className="terms-row">
          <Help name="MFE" />
          <Help name="MAE" />
          <Help name="Historical OOS" />
          <Help name="Trading bar" />
        </div>
      </Disclosure>
      <Evidence research={research} />
      <Section
        title="Across time, the result is uneven"
        note="Annual expanding-history folds · non-overlapping trades after costs"
        action={<a href="#robustness">Inspect robustness →</a>}
      >
        <div className="two-column">
          <Bars rows={research.folds} x="fold" y="net_mean" label="Mean net trade return" />
          <div className="reading-note">
            <span className="eyebrow">What to notice</span>
            <h3>2022 lost money.</h3>
            <p>The overall average hides differences between years and stocks.</p>
            <p>
              2026 is a partial historical fold through {String(research.folds.at(-1)?.test_end)},
              not a live YTD result.
            </p>
          </div>
        </div>
        <Disclosure title="Year-by-year results">
          <DataTable
            rows={research.folds}
            columns={foldColumns}
            caption="Annual walk-forward evidence"
          />
        </Disclosure>
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
          Manual collection only. No future results have been scored. First review: no earlier than{' '}
          {data.archive.config.review_dates[0]}, once the protocol's data requirements are met.
        </p>
        <a href="#paper-archive">Inspect the paper archive →</a>
      </Section>
      <Note>
        Historical evidence only. Statistical significance and future profits are unproven. Today's
        surviving stocks may give a biased picture.
      </Note>
    </>
  )
}
