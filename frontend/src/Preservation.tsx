import { useState } from 'react'
import { DataTable, Empty, Metric, Note, PageTitle, Section } from './components'
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
        Preserved decisions and input vintages. No scheduler, trading connection or prospective
        outcome scoring.
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
      <Section title="Run completion and provenance">
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
      </Section>
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
          Coverage is a snapshot, not a live connection. Rebuild the export after collection. Review
          dates: {a.config.review_dates.join(' / ')}; the protocol's minimum session and
          completeness requirements still apply.
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
        Audit evidence is separate from the frozen experiment sample. No data repair or historical
        strategy re-evaluation was performed.
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
            Original rejected raw responses were not preserved. These are newly retrieved diagnostic
            vintages; they cannot prove exactly what EXP-002 received.
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
                { key: 'affected_fraction', label: 'Fraction', format: 'percent' },
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
          <Section
            title="Exact violations"
            note="Values are displayed at round-trip precision; scientific notation preserves tiny discrepancies."
          >
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
          </Section>
        </>
      )}
      <Section title="Why this matters">
        <p>
          A close can fall just outside a transformed high or low by one representable
          floating-point step. Strict ingestion then rejects the entire history, changing sample
          composition. Small numerical discrepancies can therefore have a large effect on which
          stocks enter a study.
        </p>
        <p>
          The new vintage shows one-ULP boundary discrepancies consistent with floating-point
          adjustment arithmetic. That is an explanation supported by the numerical pattern, not
          proof of the provider's internal cause or of the original rejected response.
        </p>
        <Note>
          Remediation status: recommendation only. Original validation and frozen inputs are
          unchanged. A separately reviewed, bounded numerical policy would require deterministic
          tests and independent data-quality criteria before adoption.
        </Note>
      </Section>
      <Section
        title="Universe provenance"
        note="Current constituents are not historical membership."
      >
        <p>
          The OEF-derived static list was sourced on 2026-09-29. EXP-001 issuers, including GOOG
          alongside GOOGL, were excluded from the primary cross-sectional holdout. SPY is a
          benchmark. Interval support does not make an unverified membership file point-in-time.
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
