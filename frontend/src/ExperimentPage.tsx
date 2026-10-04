import { useState } from 'react'
import briefs from './content/experiments.json'
import { comparisonColumns, DataTable, Disclosure, Metric, Note, PageTitle } from './components'
import { docURL, type Dashboard, type Experiment } from './data'
import { Document, tradeColumns } from './Research'
import { Evidence } from './Overview'
import ExitResearch from './ExitResearch'

export default function Experiments({ data }: { data: Dashboard }) {
  const [id, setId] = useState('EXP-002')
  const selected = data.experiments.find((experiment) => experiment.id === id)
  return (
    <>
      <PageTitle eyebrow="Research notebook" title="What did we learn?">
        The short answer first. Open the evidence when you want more.
      </PageTitle>
      <div className="experiment-tabs" role="tablist" aria-label="Experiment">
        {data.experiments.map((experiment) => (
          <button
            key={experiment.id}
            role="tab"
            aria-selected={id === experiment.id}
            onClick={() => setId(experiment.id)}
          >
            <span>{experiment.id}</span>
            <strong>
              {briefs[experiment.id as keyof typeof briefs]?.title || experiment.title}
            </strong>
            <small>{experiment.status}</small>
          </button>
        ))}
      </div>
      {selected && <ExperimentBrief key={selected.id} experiment={selected} data={data} />}
      {selected?.id === 'EXP-004' && (
        <Disclosure title="Explore the exit comparisons">
          <ExitResearch data={data} />
        </Disclosure>
      )}
    </>
  )
}

function ExperimentBrief({ experiment, data }: { experiment: Experiment; data: Dashboard }) {
  const [split, setSplit] = useState('test')
  const brief = briefs[experiment.id as keyof typeof briefs]
  const r = data.exp002
  const first = data.exp001.report?.trade_summaries.find(
    (row) => row.split === 'test' && row.mode === 'non_overlapping',
  )
  const trade =
    r.status === 'available'
      ? r.tables.trade_oos_summary.find((row) => row.mode === 'non_overlapping')
      : null
  return (
    <>
      {brief && (
        <section className="experiment-brief" aria-label={`${experiment.id} short summary`}>
          <dl>
            {[
              ['Question', brief.question],
              ['Test', brief.test],
              ['Result', brief.result],
              ['Limitation', brief.limitation],
            ].map(([label, text]) => (
              <div key={label} className={label === 'Result' ? 'brief-result' : ''}>
                <dt>{label}</dt>
                <dd>{text}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      {experiment.id === 'EXP-001' && first && (
        <div className="metric-grid brief-metrics">
          <Metric
            label="Expectancy"
            value={first.average_return}
            note="Average trade after costs · historical test"
          />
          <Metric
            label="Median return"
            value={first.median_return}
            note="Middle trade after costs · historical test"
          />
          <Metric
            label="Win rate"
            value={first.win_rate}
            kind="rate"
            note="Profitable completed trades · historical test"
          />
        </div>
      )}
      {experiment.id === 'EXP-002' && r.status === 'available' && (
        <div className="metric-grid brief-metrics">
          <Metric
            label="Expectancy"
            value={trade?.average_return}
            note="Average trade after costs · historical OOS"
          />
          <Metric
            label="Stocks ahead of SPY"
            value={r.criteria.positive_excess_tickers}
            kind="integer"
            note={`Out of ${r.criteria.defined_tickers} · ten-bar paired mean · breadth test failed`}
          />
          <Metric
            label="Stocks tested"
            value={r.metadata.usable_count}
            kind="integer"
            note={`${r.metadata.requested_count} requested · current survivors`}
          />
        </div>
      )}
      {experiment.id === 'EXP-003' && data.audit.status === 'available' && (
        <div className="metric-grid brief-metrics">
          <Metric
            label="Stocks audited"
            value={data.audit.summaries?.length}
            kind="integer"
            note="All original exclusions"
          />
          <Metric
            label="Rows with issues"
            value={data.audit.affected_rows}
            kind="integer"
            note="New downloads · originals unavailable"
          />
          <Metric
            label="Prospective records"
            value={data.archive.prospective_count}
            kind="integer"
            note="Recorded before the planned entry · no scoring"
          />
        </div>
      )}
      <p className="reading-boundary">
        {experiment.id === 'EXP-003'
          ? 'This audit did not test trading performance.'
          : 'Historical evidence only. Future profitability and statistical significance are not established.'}
      </p>
      {brief && (
        <a className="next-link" href={`#${brief.link}`}>
          {brief.next} →
        </a>
      )}
      {experiment.id === 'EXP-002' && r.status === 'available' && (
        <Disclosure title="Explore the numbers">
          <Evidence research={r} />
        </Disclosure>
      )}
      {experiment.id === 'EXP-001' && data.exp001.status === 'available' && (
        <Disclosure title="Explore the numbers">
          <p className="small">
            Original five stocks · 2016-09-29–2026-09-28. These historical periods have already been
            inspected.
          </p>
          <label className="field">
            Test period
            <select value={split} onChange={(event) => setSplit(event.target.value)}>
              {['research', 'validation', 'test'].map((period) => (
                <option key={period}>{period}</option>
              ))}
            </select>
          </label>
          <DataTable
            rows={(data.exp001.comparison || []).filter((row) => row.group === split)}
            columns={comparisonColumns}
            caption="EXP-001 fixed-horizon comparisons"
          />
          <DataTable
            rows={(data.exp001.report?.trade_summaries || []).filter((row) => row.split === split)}
            columns={tradeColumns}
            caption="EXP-001 barrier results"
          />
        </Disclosure>
      )}
      {((experiment.id === 'EXP-001' && data.exp001.status !== 'available') ||
        (experiment.id === 'EXP-002' && r.status !== 'available') ||
        (experiment.id === 'EXP-003' && data.audit.status !== 'available')) && (
        <Note>
          Local results are unavailable. The summary reflects the published research record; no
          example results have been substituted.
        </Note>
      )}
      <Disclosure title="Full research record">
        <Document body={experiment.body} />
        <a href={docURL(experiment.doc)}>Open source documentation ↗</a>
      </Disclosure>
    </>
  )
}
