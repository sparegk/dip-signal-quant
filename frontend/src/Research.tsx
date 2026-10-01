import { useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Bars,
  comparisonColumns,
  DataTable,
  Empty,
  foldColumns,
  glossary,
  Help,
  Note,
  PageTitle,
  Section,
  type Column,
} from './components'
import { docURL, format, type Dashboard, type Exp2, type Row } from './data'
import { Evidence } from './Overview'

export const tradeColumns: Column[] = [
  { key: 'mode', label: 'Analysis mode' },
  { key: 'trade_count', label: 'Completed', format: 'integer' },
  { key: 'average_return', label: 'Mean net', format: 'percent' },
  { key: 'median_return', label: 'Median net', format: 'percent' },
  { key: 'win_rate', label: 'Win rate', format: 'percent' },
  { key: 'profit_factor', label: 'Profit factor', format: 'number' },
  { key: 'average_mfe', label: 'MFE', format: 'percent' },
  { key: 'average_mae', label: 'MAE', format: 'percent' },
]
export function Document({ body, source = 'EXPERIMENTS' }: { body: string; source?: string }) {
  return (
    <div className="document">
      <Markdown
        remarkPlugins={[remarkGfm]}
        components={{
          table: (props) => (
            <div className="table-scroll">
              <table {...props} />
            </div>
          ),
          a: ({ href, children }) => (
            <a href={href ? new URL(href, docURL(source)).href : undefined}>{children}</a>
          ),
        }}
      >
        {body}
      </Markdown>
    </div>
  )
}
export function Missing({ reason }: { reason?: string }) {
  return (
    <Empty title="Preserved results unavailable">
      {reason ||
        'Export the preserved local artifacts to view these tables. Documentation remains available under Experiments.'}
    </Empty>
  )
}

export function Robustness({ data }: { data: Dashboard }) {
  const r = data.exp002
  if (r.status !== 'available') return <Missing reason={r.reason} />
  const distributions = [
    ['gross', 'Ten-bar gross event mean', 'mean'],
    ['excess', 'Ten-bar matched-SPY excess', 'mean_excess_return'],
    ['expectancy', 'Non-overlapping net expectancy', 'net_expectancy'],
  ]
  return (
    <>
      <PageTitle eyebrow="EXP-002 · Historical OOS" title="How broadly does the behavior survive?">
        A static current-constituent universe; historical windows have been inspected and are
        consumed.
      </PageTitle>
      <Note warning>
        <strong>Registered breadth criterion failed.</strong> {r.criteria.positive_excess_tickers}/
        {r.criteria.defined_tickers} ticker excess means were positive. A strict majority was
        required. Favorable ten-bar fold comparisons: {r.criteria.favorable_folds}/
        {r.criteria.fold_count}.
      </Note>
      <Section
        title="Repeated chronological windows"
        note="Frozen parameters. History expands from 2016-09-29; complete outcome paths must fit inside each OOS fold."
      >
        <Bars rows={r.folds} x="fold" y="net_mean" label="Non-overlapping mean net trade return" />
        <DataTable rows={r.folds} columns={foldColumns} caption="Annual walk-forward results" />
        <details>
          <summary>Exact fold boundaries</summary>
          <DataTable
            rows={r.folds}
            columns={[
              'fold',
              'history_start',
              'history_end',
              'test_start',
              'test_end',
              'partial_year',
            ].map((key) => ({ key, label: key.replaceAll('_', ' ') }))}
            caption="Chronological fold boundaries"
          />
        </details>
      </Section>
      <Section
        title="Cross-sectional distribution"
        note={`${r.metadata.usable_count} usable of ${r.metadata.requested_count} requested tickers. Losing names remain in the sample; histories have unequal lengths.`}
      >
        <div className="distribution-grid">
          {distributions.map(([key, title, metric]) => {
            const d = r.tables.distribution.find(
              (x) =>
                x.metric === metric &&
                (key === 'expectancy' ? x.kind === 'trade' : x.horizon === 10),
            )
            return (
              <div key={key}>
                <h3>{title}</h3>
                <Bars
                  rows={r.histograms[key]}
                  x="center"
                  y="count"
                  percent={false}
                  label="Ticker count per return bin"
                  height={210}
                />
                <p className="stat-line">
                  Positive {String(d?.positive_count ?? '—')} · Negative{' '}
                  {String(d?.negative_count ?? '—')}
                </p>
                <p className="small">
                  Median {format(d?.median)}
                  <br />
                  Q1 {format(d?.q25)} / Q3 {format(d?.q75)}
                </p>
              </div>
            )
          })}
        </div>
        <DataTable
          rows={r.tables.trade_ticker_summary.filter((x) => x.mode === 'non_overlapping')}
          columns={[{ key: 'ticker', label: 'Ticker' }, ...tradeColumns.slice(1)]}
          caption="All ticker net expectancies"
        />
        <details>
          <summary>All ticker ten-bar event and excess results</summary>
          <DataTable
            rows={r.tables.ticker_summary.filter(
              (row) => row.selection === 'events' && row.horizon === 10,
            )}
            columns={[
              { key: 'ticker', label: 'Ticker' },
              { key: 'count', label: 'Completed', format: 'integer' },
              { key: 'mean', label: 'Event gross', format: 'percent' },
              { key: 'benchmark_mean', label: 'Matched SPY', format: 'percent' },
              { key: 'mean_excess_return', label: 'Paired excess', format: 'pp' },
              { key: 'median', label: 'Event median', format: 'percent' },
            ]}
            caption="All ticker event and excess means"
          />
        </details>
      </Section>
      <Concentration research={r} />
      <Section
        title="Market context, not a fitted classifier"
        note="SPY close above/below its trailing 200-session average, known after signal-session close. Descriptive subgroup analysis."
      >
        <div className="two-column">
          <div>
            <h3>Gross ten-bar events</h3>
            <DataTable
              rows={r.tables.regime_summary.filter(
                (x) => x.selection === 'events' && x.horizon === 10,
              )}
              columns={[
                { key: 'regime', label: 'SPY regime' },
                { key: 'observations', label: 'Events', format: 'integer' },
                { key: 'count', label: 'Completed', format: 'integer' },
                { key: 'mean', label: 'Mean gross', format: 'percent' },
                { key: 'mean_excess_return', label: 'Paired Δ SPY', format: 'pp' },
              ]}
              caption="Regime event outcomes"
            />
          </div>
          <div>
            <h3>Non-overlapping trades</h3>
            <DataTable
              rows={r.tables.trade_regime_summary.filter((x) => x.mode === 'non_overlapping')}
              columns={[{ key: 'regime', label: 'SPY regime' }, ...tradeColumns.slice(1, 5)]}
              caption="Regime trade outcomes"
            />
          </div>
        </div>
      </Section>
      <Section
        title="Frequency and component count"
        note="Frequency is normalized per 252 ready observations, not calendar years. Components are correlated."
      >
        <Bars
          rows={r.folds}
          x="fold"
          y="frequency"
          percent={false}
          label="Events per 252 ready observations"
        />
        <DataTable
          rows={r.tables.frequency_fold}
          columns={[
            { key: 'fold', label: 'Fold' },
            { key: 'ready', label: 'Ready rows', format: 'integer' },
            { key: 'events', label: 'Events', format: 'integer' },
            { key: 'condition_fraction_ready', label: 'Condition days', format: 'percent' },
            { key: 'events_per_252_ready', label: 'Events / 252', format: 'number' },
          ]}
          caption="Event frequency by fold"
        />
        <DataTable
          rows={r.tables.component_oos_summary.filter((x) => x.horizon === 10)}
          columns={[
            { key: 'dip_component_count', label: 'Components' },
            { key: 'count', label: 'Completed', format: 'integer' },
            { key: 'mean', label: '10-bar gross', format: 'percent' },
            { key: 'mean_excess_return', label: 'Paired Δ SPY', format: 'pp' },
          ]}
          caption="Component subgroup outcomes"
        />
      </Section>
      <Note>
        Positive pooled results do not establish broad incremental value. The negative 2022 trade
        result, failed breadth criterion, overlapping events, survivorship selection, and small
        subgroups remain material. Event bootstrap intervals do not test the significance of
        baseline differences.
      </Note>
    </>
  )
}
function Concentration({ research: r }: { research: Exp2 }) {
  return (
    <Section
      title="How much comes from a handful of names?"
      note="Equal-notional return sums. These are descriptive contributions, not allocated capital or portfolio returns."
    >
      <div className="two-column">
        {[
          ['net_trades', 'Net trade contribution'],
          ['event_excess_10', 'Ten-bar excess contribution'],
        ].map(([key, title]) => {
          const c = r.metadata.concentration[key]
          const rows = r.tables[`contribution_${key}`]
          return (
            <div key={key}>
              <h3>{title}</h3>
              <div className="concentration-value">
                {format(c.top5_positive_share)}
                <span>Top five share of positive ticker contributions</span>
              </div>
              <p className="small">
                Registered flag: &gt; {format(r.criteria.concentration_threshold)} ·{' '}
                {Number(c.top5_positive_share) > r.criteria.concentration_threshold
                  ? 'Flagged'
                  : 'Not flagged'}
              </p>
              <p className="small">
                Total sum {format(c.total_sum, 'number')} · Positive sum{' '}
                {format(c.positive_sum, 'number')} · Negative sum {format(c.negative_sum, 'number')}
                <br />
                Units: summed return fractions, not percentages of portfolio capital.
              </p>
              <DataTable
                rows={rows}
                columns={[
                  { key: 'ticker', label: 'Ticker' },
                  { key: 'return_sum', label: 'Return sum', format: 'number' },
                  { key: 'mean', label: 'Mean', format: 'percent' },
                  { key: 'positive_share', label: 'Positive share', format: 'percent' },
                ]}
                pageSize={5}
                caption={title}
              />
            </div>
          )
        })}
      </div>
    </Section>
  )
}

export function Backtest({ data }: { data: Dashboard }) {
  const r = data.exp002
  return (
    <>
      <PageTitle
        eyebrow="Frozen illustrative specification"
        title="Outcomes, with execution assumptions"
      >
        Two ways to summarize the same events. Neither is an historical portfolio.
      </PageTitle>
      <div className="protocol-grid">
        <div>
          <span>ENTRY</span>
          <h3>Next observed session open</h3>
          <p>No signal-close fill. Adjusted daily OHLC.</p>
        </div>
        <div>
          <span>EXIT</span>
          <h3>+10% / −7% / 10 bars</h3>
          <p>Target / stop / timeout at the final close.</p>
        </div>
        <div>
          <span>FRICTION</span>
          <h3>1 bp + 5 bp per side</h3>
          <p>Commission plus slippage, applied through fills.</p>
        </div>
        <div>
          <span>AMBIGUITY</span>
          <h3>Conservative stop first</h3>
          <p>Gap-aware open fills; both barriers hit in one daily bar resolve to the stop.</p>
        </div>
      </div>
      <Note>
        Independent analysis allows overlapping events. Non-overlapping mode suppresses new entries
        while the same ticker is already held. Outcomes that lack a complete required window are
        censored, including at fold boundaries.
      </Note>
      {r.status !== 'available' ? (
        <Missing />
      ) : (
        <>
          <Section
            title="EXP-002 pooled OOS trades"
            note="2021–2026 partial · all usable tickers · mean and median after costs"
          >
            <DataTable
              rows={r.tables.trade_oos_summary}
              columns={tradeColumns}
              caption="Barrier strategy modes"
            />
            <DataTable
              rows={r.exit_counts}
              columns={[
                { key: 'mode', label: 'Mode' },
                { key: 'exit_reason', label: 'Exit' },
                { key: 'count', label: 'Trades', format: 'integer' },
              ]}
              caption="TP SL time exit counts"
            />
          </Section>
          <Section title="Excluded opportunities remain visible">
            <DataTable
              rows={r.tables.trade_oos_summary}
              columns={[
                { key: 'mode', label: 'Mode' },
                ...[
                  'candidate_count',
                  'excluded_count',
                  'overlap',
                  'no_next_bar',
                  'incomplete_window',
                  'ambiguous_exits',
                ].map((key) => ({ key, label: key.replaceAll('_', ' '), format: 'integer' })),
              ]}
              caption="Trade censoring and overlap"
            />
          </Section>
        </>
      )}
      <Section title="What these ledgers cannot tell you">
        <p>
          <Help name="Sharpe" />, <Help name="Sortino" />, capital drawdown and compound portfolio
          returns are not defined for these pooled event ledgers. Overlapping exposure, capital
          allocation and portfolio constraints would need a separately specified experiment.
        </p>
        <p>
          Barrier excursions are restricted by execution-path conventions; daily OHLC cannot reveal
          intraday ordering. The strategy and cost model remain illustrative and uncalibrated.
        </p>
        <a href={docURL('BACKTESTING')}>Read execution and metric definitions ↗</a>
        <details>
          <summary>Metric and research definitions</summary>
          <dl className="facts">
            {Object.entries(glossary).map(([name, definition]) => (
              <div key={name} className="definition">
                <dt>
                  <Help name={name} />
                </dt>
                <dd>{definition}</dd>
              </div>
            ))}
          </dl>
        </details>
      </Section>
    </>
  )
}

export function Experiments({ data }: { data: Dashboard }) {
  const [id, setId] = useState('EXP-002')
  const [split, setSplit] = useState('test')
  const selected = data.experiments.find((x) => x.id === id)
  return (
    <>
      <PageTitle eyebrow="Research registry" title="Protocols before conclusions">
        All three historical investigations are complete. The inspected samples are consumed;
        prospective outcome evaluation has not begun.
      </PageTitle>
      <div className="experiment-tabs" role="tablist" aria-label="Experiment">
        {data.experiments.map((e) => (
          <button role="tab" aria-selected={id === e.id} key={e.id} onClick={() => setId(e.id)}>
            <span>{e.id}</span>
            <strong>
              {e.id === 'EXP-001'
                ? 'Baseline evaluation'
                : e.id === 'EXP-002'
                  ? 'Cross-sectional robustness'
                  : 'Data quality & preservation'}
            </strong>
            <small>{e.status} · fixed protocol</small>
          </button>
        ))}
      </div>
      {id === 'EXP-002' && data.exp002.status === 'available' && (
        <>
          <Note warning>
            Registered cross-sectional breadth failed. Positive pooled returns are not proof of an
            edge.
          </Note>
          <Evidence research={data.exp002} />
        </>
      )}
      {id === 'EXP-001' && data.exp001.status === 'available' && (
        <Section
          title="First fixed-specification evaluation"
          note="AAPL, MSFT, NVDA, AMZN, GOOGL · 2016-09-29–2026-09-28 · SPY benchmark"
        >
          <label className="field">
            Chronological split
            <select value={split} onChange={(e) => setSplit(e.target.value)}>
              {['research', 'validation', 'test'].map((s) => (
                <option key={s}>{s}</option>
              ))}
            </select>
          </label>
          <DataTable
            rows={(data.exp001.comparison || []).filter((x) => x.group === split)}
            columns={comparisonColumns}
            caption="EXP-001 fixed-horizon comparisons"
          />
          <DataTable
            rows={(data.exp001.report?.trade_summaries || []).filter((x) => x.split === split)}
            columns={tradeColumns}
            caption="EXP-001 barrier results"
          />
          <Note>
            The test sample was inspected and is consumed. Its near-zero net expectancy and losing
            stocks remain part of the research record.
          </Note>
        </Section>
      )}
      {selected && (
        <Section
          title={selected.title}
          note="Canonical protocol, hypothesis, universe, results, limitations and interpretation"
          action={<a href={docURL(selected.doc)}>Source documentation ↗</a>}
        >
          <Document body={selected.body} />
        </Section>
      )}
    </>
  )
}

export function ResearchLog({ data }: { data: Dashboard }) {
  return (
    <>
      <PageTitle eyebrow="Chronological record" title="Research log">
        Hypotheses, findings and decisions, read directly from the repository.
      </PageTitle>
      <div className="timeline">
        {data.research_log.map((entry, i) => (
          <article key={i}>
            <time>{entry.date}</time>
            <details open={i === 0}>
              <summary>{entry.title.replace(/^\d{4}-\d{2}-\d{2}\s*[—–-]?\s*/, '')}</summary>
              <Document body={entry.body} source="RESEARCH_LOG" />
            </details>
          </article>
        ))}
      </div>
      <a href={docURL('RESEARCH_LOG')}>Full research log ↗</a>
    </>
  )
}
export function Roadmap({ data }: { data: Dashboard }) {
  return (
    <>
      <PageTitle eyebrow="Scope & status" title="What exists. What remains open.">
        Status comes from ROADMAP.md. Future functionality is not implied by this interface.
      </PageTitle>
      <div className="roadmap-grid">
        {[
          ['completed', 'Completed'],
          ['in_progress', 'In progress'],
          ['not_started', 'Not started'],
          ['prospective', 'Prospective review'],
        ].map(([status, title]) => (
          <section key={status}>
            <h2>{title}</h2>
            {data.roadmap
              .filter((r) => r.status === status)
              .map((r) => (
                <div className="roadmap-item" key={r.title}>
                  <span className={status === 'completed' ? 'positive' : ''}>
                    {status === 'completed' ? '✓' : '○'}
                  </span>
                  {r.title}
                </div>
              ))}
            {!data.roadmap.some((r) => r.status === status) && (
              <p className="small">No milestone currently marked {title.toLowerCase()}.</p>
            )}
          </section>
        ))}
      </div>
      <Note>
        V1 is frozen. No scoring model, automated scanner, broker execution or prospective
        performance assessment is implemented by this frontend.
      </Note>
    </>
  )
}
