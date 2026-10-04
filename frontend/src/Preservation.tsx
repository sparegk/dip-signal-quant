import { useState } from 'react'
import { DataTable, Disclosure, Empty, Metric, Note, PageTitle, Section } from './components'
import { docURL, format, type ArchiveRecord, type Dashboard, type Row } from './data'
import { Document, Missing } from './Research'

export function PaperArchive({ data }: { data: Dashboard }) {
  const a = data.archive
  const [tab, setTab] = useState('prospective')
  const [selected, setSelected] = useState<ArchiveRecord | null>(null)
  const rows = a.records.filter((r) =>
    tab === 'other'
      ? !['prospective', 'retrospective'].includes(r.classification)
      : r.classification === tab,
  )
  const table: Row[] = rows.map((r) => ({
    record_id: r.record_id,
    ticker: r.ticker,
    session: r.session,
    published_at: r.published_at,
    classification: r.classification,
    status: r.status,
    event: r.values?.dip_event_v1 ?? null,
    ready: r.values?.dip_ready_v1 ?? null,
    components: r.values?.dip_component_count ?? null,
  }))
  return (
    <>
      <PageTitle eyebrow="EXP-003 · Collection only" title="Paper-signal archive">
        A record of what the system knew at the time. Collection is manual; future returns are not
        scored.
      </PageTitle>
      <div className="scope-line">
        <strong>Manual archive · {a.status.replaceAll('_', ' ')}</strong>
        <span>
          Effective session {a.config.effective_session} · Export coverage cutoff {a.as_of}
        </span>
      </div>
      <div className="metric-grid">
        <Metric
          label="Universe"
          value={a.config.universe.length}
          kind="integer"
          note="Frozen requested names, not historical winners"
        />
        <Metric
          label="Prospective records"
          value={a.prospective_count}
          kind="integer"
          note="Before intended execution; includes non-events"
        />
        <Metric
          label="Retrospective records"
          value={a.retrospective_count}
          kind="integer"
          note="Replay never becomes a fresh temporal holdout"
        />
        <Metric
          label="Preserved non-events"
          value={a.non_event_count}
          kind="integer"
          note="Across all collection classifications"
        />
        <Metric
          label="Unavailable inputs"
          value={a.failure_count}
          kind="integer"
          note="Retained failures, not zero-signal observations"
        />
        <Metric
          label="Runs preserved"
          value={a.runs.length}
          kind="integer"
          note="Completion and corrections audited separately"
        />
      </div>
      <Section
        title="Preserved observations"
        note="Non-events and failures remain visible alongside events."
      >
        <div className="tabs" role="tablist" aria-label="Archive classification">
          {[
            ['prospective', 'Prospective'],
            ['retrospective', 'Historical replay'],
            ['other', 'Late / stale / unavailable'],
          ].map(([key, label]) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => {
                setTab(key)
                setSelected(null)
              }}
            >
              {label}
            </button>
          ))}
        </div>
        {tab === 'prospective' && rows.length === 0 ? (
          <Empty title="Prospective archive initialized — awaiting first eligible completed session.">
            No genuine prospective sample has been substituted with historical replay.
          </Empty>
        ) : (
          <>
            <Note warning={tab !== 'prospective'}>
              {tab === 'retrospective'
                ? 'Retrospective records. These dates were already observed; none count toward the prospective holdout.'
                : tab === 'other'
                  ? 'Timing or input availability did not establish a genuine prospective decision.'
                  : 'Genuine prospective classification is verified by the archive, not inferred from a date label.'}
            </Note>
            <DataTable
              rows={table}
              columns={[
                { key: 'ticker', label: 'Ticker' },
                { key: 'session', label: 'Session' },
                { key: 'published_at', label: 'Recorded UTC' },
                { key: 'status', label: 'Input status' },
                { key: 'ready', label: 'Ready' },
                { key: 'event', label: 'Event' },
                { key: 'components', label: 'Components', format: 'integer' },
              ]}
              caption="Archived signal decisions"
              onSelect={(row) =>
                setSelected(rows.find((r) => r.record_id === row.record_id) || null)
              }
            />
          </>
        )}
        {selected && (
          <div className="detail-panel">
            <h3>
              {selected.ticker} · {selected.session}
            </h3>
            <dl className="facts">
              <dt>Expected execution opportunity</dt>
              <dd>
                {selected.expected_entry_timestamp || 'Unavailable'} (scheduled; actual entry not
                yet observed)
              </dd>
              <dt>Context preservation</dt>
              <dd>{selected.context_classification || 'No context sidecar preserved'}</dd>
              <dt>Classification</dt>
              <dd>{selected.classification}</dd>
              <dt>Record identity</dt>
              <dd>{selected.record_id}</dd>
              <dt>Recorded UTC</dt>
              <dd>{selected.published_at}</dd>
              <dt>Retrieved vintage</dt>
              <dd>{selected.retrieved_at || 'Unavailable'}</dd>
              <dt>Code revision</dt>
              <dd className="hash">{selected.code_revision}</dd>
              <dt>Configuration SHA-256</dt>
              <dd className="hash">{selected.config_hash}</dd>
              <dt>Input SHA-256</dt>
              <dd className="hash">{selected.input_hash || 'No preserved validated input'}</dd>
            </dl>
            {selected.decision_context && (
              <Disclosure title="Additional information known at signal time">
                <p>
                  Regime: {selected.decision_context.regime}; mature prior-zone visits:{' '}
                  {selected.decision_context.prior_successful_visits}. Context timing is separate
                  from the original signal classification.
                </p>
                <DataTable
                  rows={Object.entries(selected.decision_context.features).map(
                    ([feature, value]) => ({ feature, value }),
                  )}
                  columns={[
                    { key: 'feature', label: 'Causal feature' },
                    { key: 'value', label: 'Recorded value', format: 'number' },
                  ]}
                  caption="Preserved decision context"
                />
              </Disclosure>
            )}
            {selected.values ? (
              <DataTable
                rows={Object.entries(selected.values).map(([key, value]) => ({
                  key,
                  value: typeof value === 'number' ? String(value) : String(value),
                }))}
                columns={[
                  { key: 'key', label: 'Signal-time field' },
                  { key: 'value', label: 'Preserved value' },
                ]}
                caption="Preserved decision values"
                pageSize={30}
              />
            ) : (
              <Note warning>{selected.error}</Note>
            )}
            <Note>
              Outcome fields are separate and currently unpopulated. Evaluation requires the
              registered review gate and separate authorization.
            </Note>
          </div>
        )}
      </Section>
      <Disclosure title="Collection history and data sources">
        <DataTable
          rows={a.runs}
          columns={[
            { key: 'run_id', label: 'Run' },
            { key: 'session', label: 'Session' },
            { key: 'published_at', label: 'Last collection UTC' },
            { key: 'status', label: 'Completion' },
            { key: 'mode', label: 'Mode' },
            { key: 'code_dirty', label: 'Dirty revision' },
            { key: 'corrects', label: 'Corrects' },
          ]}
          caption="Archive run provenance"
        />
        <details>
          <summary>Frozen requested universe ({a.config.universe.length})</summary>
          <p className="ticker-list">{a.config.universe.join(' · ')}</p>
        </details>
      </Disclosure>
      <Section
        title="Coverage and missing runs"
        note="A missing collection is not a run with no signals."
      >
        {a.coverage.length ? (
          <DataTable
            rows={a.coverage}
            columns={['session', 'status', 'prospective', 'expected'].map((key) => ({
              key,
              label: key,
            }))}
            caption="Registered collection coverage"
          />
        ) : (
          <p>No eligible session deadline is due at this export's coverage cutoff.</p>
        )}
        <p className="small">
          Exported snapshot, not live coverage. Review dates: {a.config.review_dates.join(' / ')};
          enough complete sessions are also required.
        </p>
      </Section>
      <details>
        <summary>Collection, correction and holdout review policy</summary>
        <Document body={data.documents.PAPER_ARCHIVE || ''} source="PAPER_ARCHIVE" />
      </details>
    </>
  )
}

export function DataQuality({ data }: { data: Dashboard }) {
  const a = data.audit
  return (
    <>
      <PageTitle
        eyebrow="EXP-003 · Historical diagnostic audit"
        title="Small discrepancies. Real research consequences."
      >
        Tiny price inconsistencies can exclude an entire stock. This audit checks the data, not
        trading performance.
      </PageTitle>
      {a.status !== 'available' ? (
        <Missing reason={a.reason} />
      ) : (
        <>
          <div className="metric-grid">
            <Metric
              label="Audited tickers"
              value={a.summaries?.length}
              kind="integer"
              note="All EXP-002 OHLC exclusions"
            />
            <Metric
              label="Audited rows"
              value={a.rows}
              kind="integer"
              note="New diagnostic retrieval vintage"
            />
            <Metric
              label="Affected rows"
              value={a.affected_rows}
              kind="integer"
              note="Strict original ingestion rules retained"
            />
          </div>
          <Note warning>
            The original rejected downloads were not saved. These new copies cannot prove exactly
            what the experiment received.
          </Note>
          <Section
            title="Every excluded ticker"
            note="No replacements, tolerance widening, row deletion, price clipping or reinsertion into EXP-002."
          >
            <DataTable
              rows={a.summaries || []}
              columns={[
                { key: 'ticker', label: 'Ticker' },
                { key: 'rows', label: 'Rows', format: 'integer' },
                { key: 'affected_rows', label: 'Affected', format: 'integer' },
                { key: 'affected_fraction', label: 'Fraction', format: 'rate' },
                {
                  key: 'max_absolute_gap',
                  label: 'Max absolute gap',
                  render: (r) => Number(r.max_absolute_gap).toExponential(3),
                },
                {
                  key: 'max_relative_gap',
                  label: 'Relative gap',
                  render: (r) => Number(r.max_relative_gap).toExponential(3),
                },
                { key: 'max_spacing_units', label: 'ULPs', format: 'number' },
                { key: 'vintage', label: 'Vintage' },
              ]}
              caption="All excluded ticker diagnostics"
              pageSize={25}
            />
          </Section>
          <Disclosure title="Inspect exact prices and validation errors">
            <p className="small">Full precision is kept so tiny differences remain visible.</p>
            <DataTable
              rows={a.violations || []}
              columns={[
                { key: 'ticker', label: 'Ticker' },
                { key: 'session', label: 'Session' },
                { key: 'rule', label: 'Rule' },
                ...['open', 'high', 'low', 'close'].map((key) => ({ key, label: key })),
                {
                  key: 'absolute_gap',
                  label: 'Absolute gap',
                  render: (r) => String(r.absolute_gap),
                },
                { key: 'spacing_units', label: 'ULPs', format: 'number' },
              ]}
              caption="Offending OHLC values"
            />
          </Disclosure>
        </>
      )}
      <Section title="Why this matters">
        <p>
          Some newly downloaded closing prices differed from their high/low boundary by one tiny
          computer-number step. Strict checks reject a stock history for that mismatch.
        </p>
        <p>
          Rounding during price adjustment is a plausible explanation. The provider's exact cause is
          not established.
        </p>
        <Note>
          No repair was applied. Any tolerance change needs a separate data-quality review and
          tests.
        </Note>
      </Section>
      <Section
        title="Universe provenance"
        note="Current constituents are not historical membership."
      >
        <p>
          The list came from OEF holdings on 2026-09-29. Earlier-tested companies were excluded; SPY
          was the comparison. This list does not tell us which companies belonged historically.
        </p>
        {data.exp002.status === 'available' && (
          <p>
            Requested {data.exp002.metadata.requested_count} · usable{' '}
            {data.exp002.metadata.usable_count} · excluded {data.exp002.metadata.excluded_count}.
            Survivorship and data-quality selection remain.
          </p>
        )}
        <a href={docURL('UNIVERSE_PROVENANCE')}>Historical membership sources and limitations ↗</a>
      </Section>
      <details>
        <summary>Canonical audit findings and recommendations</summary>
        <Document
          body={data.documents.DATA_QUALITY_AUDIT || data.documents.DATA_QUALITY || ''}
          source="DATA_QUALITY_AUDIT"
        />
      </details>
    </>
  )
}
