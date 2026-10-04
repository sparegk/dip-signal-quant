import { useState } from 'react'
import { Bars, DataTable, Disclosure, Note, PageTitle, Section, type Column } from './components'
import { type Dashboard } from './data'
import { Document, Missing } from './Research'

const groupColumns: Column[] = [
  { key: 'group', label: 'Group' },
  { key: 'events', label: 'Events', format: 'integer' },
  { key: 'completed', label: 'Complete', format: 'integer' },
  { key: 'mean', label: 'Gross return', format: 'percent' },
  { key: 'median', label: 'Median', format: 'percent' },
  { key: 'excess', label: 'Matched-SPY excess', format: 'pp' },
  { key: 'win_rate', label: 'Positive outcomes', format: 'rate' },
  { key: 'mfe', label: 'MFE', format: 'percent' },
  { key: 'mae', label: 'MAE', format: 'percent' },
]
const analyses = [
  ['dip_component_count', 'Component count'],
  ['combination', 'Exact component combinations'],
  ['component_presence', 'Component presence'],
  ['return_5d', 'Recent momentum'],
  ['drawdown_change_5', 'Drawdown acceleration'],
  ['atr_pct_14', 'ATR / close'],
  ['relative_volume_20d', 'Relative volume'],
  ['relative_return_10d', 'Relative weakness'],
  ['regime', 'SPY 200-day average'],
  ['benchmark_return_20d', 'SPY trailing return'],
  ['benchmark_drawdown_20d', 'SPY trailing drawdown'],
  ['benchmark_volatility_20d', 'SPY trailing volatility'],
  ['support_group', 'Prior successful dip zone'],
  ['entry_gap', 'Signal close → next open gap'],
]
export function Diagnosis({ data }: { data: Dashboard }) {
  const [analysis, setAnalysis] = useState('combination')
  const [horizon, setHorizon] = useState(10)
  const d = data.diagnosis
  return (
    <>
      <PageTitle
        eyebrow="Exploratory historical analysis · not parameter selection"
        title="Why isn't V1 stronger yet?"
      >
        Separate market rebound, signal quality and exit behavior.
      </PageTitle>
      <Note warning>
        <strong>What works:</strong> pooled rebounds are positive.{' '}
        <strong>What remains weak:</strong> stock-level SPY excess lacks breadth; 2022 struggled;
        adaptive exits increase tail losses. None is fresh validation.
      </Note>
      <Section
        title="Signal frequency and quality"
        note="Frequent dips can be ordinary market weakness. More active components do not guarantee a stronger outcome."
      >
        <p>
          V1's four components share price information. Component groups below describe existing V1
          events; they do not estimate independent causes.
        </p>
        {data.exp002.status === 'available' && (
          <Disclosure title="How frequent are the signals?">
            <DataTable
              rows={data.exp002.tables.frequency_fold}
              columns={[
                { key: 'fold', label: 'Year' },
                { key: 'events', label: 'Events', format: 'integer' },
                { key: 'condition_fraction_ready', label: 'Condition days', format: 'rate' },
                { key: 'events_per_252_ready', label: 'Events / 252 ready', format: 'number' },
              ]}
              caption="Signal frequency by year"
            />
            <p>
              Frequency alone cannot establish that V1 is too permissive. These rates do not
              authorize tightening it.
            </p>
          </Disclosure>
        )}
        {d?.status === 'available' && d.tables ? (
          <>
            <div className="filters">
              <label>
                Question
                <select value={analysis} onChange={(e) => setAnalysis(e.target.value)}>
                  {analyses.map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Forward bars
                <select value={horizon} onChange={(e) => setHorizon(Number(e.target.value))}>
                  {[1, 3, 5, 10, 20].map((n) => (
                    <option key={n}>{n}</option>
                  ))}
                </select>
              </label>
            </div>
            <DataTable
              rows={d.tables.groups.filter((r) => r.analysis === analysis && r.horizon === horizon)}
              columns={groupColumns}
              caption="Exploratory diagnostic groups"
            />
            <p className="small">
              A = drawdown; B = price z-score; C = proximity to recent low; D = relative weakness.
              Low/middle/high boundaries were recorded before calculation. Unknown inputs remain
              visible. Groups can overlap and have unequal sample sizes.
            </p>
            <Disclosure title="Exact methods and grouping boundaries">
              <Document
                body={data.documents.RESEARCH_DIAGNOSIS || ''}
                source="RESEARCH_DIAGNOSIS"
              />
            </Disclosure>
          </>
        ) : (
          <Missing reason={d?.reason} />
        )}
      </Section>
      {d?.status === 'available' && d.tables && (
        <>
          <Section
            title="How long does the rebound take?"
            note="Only complete ten-bar paths. A high-price target touch is an opportunity, not an assumed fill."
          >
            <DataTable
              rows={d.tables.timing.filter((r) => r.group === 'all')}
              columns={[
                { key: 'metric', label: 'Path question' },
                { key: 'complete_paths', label: 'Complete paths', format: 'integer' },
                { key: 'reached', label: 'Reached', format: 'integer' },
                { key: 'fraction', label: 'Share', format: 'rate' },
                {
                  key: 'median_bars_if_reached',
                  label: 'Median bars if reached',
                  format: 'number',
                },
              ]}
              caption="Time to rebound"
            />
            <Bars
              rows={d.tables.groups
                .filter((r) => r.analysis === 'all_events')
                .map((r) => ({ ...r, label: `${r.horizon} bars` }))}
              x="label"
              y="mean"
              label="Gross return by holding horizon"
            />
          </Section>
          <Disclosure title="Why do stocks differ?">
            <DataTable
              rows={d.tables.correlations}
              columns={[
                { key: 'feature', label: 'Signal-time feature' },
                { key: 'outcome', label: 'Ticker outcome' },
                { key: 'tickers', label: 'Tickers', format: 'integer' },
                { key: 'spearman', label: 'Rank correlation', format: 'number' },
              ]}
              caption="Ticker heterogeneity correlations"
            />
            <p>
              Correlations describe ticker averages and do not identify a tradable whitelist. Small
              samples, shared market moves and unequal histories can distort them.
            </p>
            <DataTable
              rows={d.tables.tickers}
              columns={[
                { key: 'ticker', label: 'Ticker' },
                ...groupColumns.slice(1),
                { key: 'events_per_252', label: 'Events / 252', format: 'number' },
              ]}
              caption="All ticker diagnosis"
            />
          </Disclosure>
          <Disclosure title="What did losing events look like at signal time?">
            <DataTable
              rows={d.tables.outcome_covariates || []}
              columns={[
                { key: 'group', label: 'Ten-bar gross outcome' },
                { key: 'completed', label: 'Events', format: 'integer' },
                { key: 'return_5d', label: 'Trailing 5-bar momentum', format: 'percent' },
                { key: 'drawdown_change_5', label: '5-bar drawdown change', format: 'pp' },
                { key: 'atr_pct_14', label: 'ATR / close', format: 'percent' },
                { key: 'relative_volume_20d', label: 'Relative volume', format: 'number' },
                { key: 'relative_return_10d', label: 'Trailing weakness vs SPY', format: 'pp' },
                { key: 'entry_gap', label: 'Next-open gap (later)', format: 'percent' },
              ]}
              caption="Signal-time features grouped by future outcome"
            />
            <p>
              The outcome labels are future research information. These mean differences cannot be
              used as a causal classifier or a new filter.
            </p>
          </Disclosure>
        </>
      )}
      <Section title="Repeated dips and entry timing" note="Hypotheses, not new rules.">
        <p>
          Prior-zone groups require a completed successful earlier dip before the current signal.
          The available diagnostic history starts in 2021, so missing earlier visits limit this
          comparison.
        </p>
        <p>
          Next-open gaps occur after the signal. A gap filter would require a separately registered
          entry decision. V1's entry remains unchanged.
        </p>
      </Section>
      <Section title="Exit problem or signal problem?">
        <p>
          Positive raw returns can coexist with weak SPY excess. Exits determine which part of the
          path becomes a realized return; they cannot establish stock-specific information by
          themselves.
        </p>
        <a href="#exit-research">Compare the same signals under different exits →</a>
      </Section>
      <Note>
        No group becomes a strategy here. Fresh validation must come from the prospective archive;
        retrospective replay never counts.
      </Note>
      <HypothesisList data={data} />
    </>
  )
}
export function Hypotheses({ data }: { data: Dashboard }) {
  return (
    <>
      <PageTitle eyebrow="Hypothesis registry" title="What deserves a fresh test?">
        Ranked ideas, not validated improvements.
      </PageTitle>
      <Note>EXP-005 is proposed only. No new experiment or optimization has begun.</Note>
      <HypothesisList data={data} />
      <Disclosure title="Proposed EXP-005 protocol">
        <Document body={data.documents.EXP005_PROPOSAL || ''} source="EXP005_PROPOSAL" />
      </Disclosure>
    </>
  )
}
function HypothesisList({ data }: { data: Dashboard }) {
  return (
    <Section
      title="Candidate future hypotheses"
      note="Rank balances intuition, current evidence, simplicity, generalizability, overfitting risk and prospective feasibility."
    >
      {(data.hypotheses || []).map((h) => (
        <Disclosure key={h.id} title={`${h.rank}. ${h.id} · ${h.name} — ${h.status}`}>
          <p>
            <strong>Why:</strong> {h.motivation}
          </p>
          <p>
            <strong>Evidence:</strong> {h.evidence}
          </p>
          <p>
            <strong>Mechanism:</strong> {h.mechanism}
          </p>
          <p>
            <strong>Risk:</strong> {h.overfitting_risk}
          </p>
          <p>
            <strong>Future test:</strong> {h.future_test}
          </p>
        </Disclosure>
      ))}
      {!data.hypotheses?.length && <p>Hypothesis registry not exported yet.</p>}
    </Section>
  )
}
