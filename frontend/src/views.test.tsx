import { fireEvent, render, screen, within, waitFor } from '@testing-library/react'
import { expect, it } from 'vitest'
import { PaperArchive } from './Preservation'
import Experiments from './ExperimentPage'
import { DataTable, Help } from './components'
import type { Dashboard } from './data'

const fixture = {
  documents: {},
  experiments: [
    {
      id: 'EXP-001',
      title: 'EXP-001 Fixed baseline',
      status: 'complete',
      doc: 'EXPERIMENTS',
      body: 'Hypothesis: mean reversion.\n\nMixed results retained.',
    },
    {
      id: 'EXP-002',
      title: 'EXP-002 Robustness',
      status: 'complete',
      doc: 'EXPERIMENTS',
      body: 'Registered breadth criterion failed.',
    },
    {
      id: 'EXP-003',
      title: 'EXP-003 Audit',
      status: 'complete',
      doc: 'EXPERIMENTS',
      body: 'No data repair.',
    },
  ],
  exp001: { status: 'missing' },
  exp002: { status: 'missing' },
  archive: {
    status: 'initialized',
    as_of: '2026-10-01T00:00:00Z',
    config: {
      universe: ['AA', 'BB'],
      effective_session: '2026-10-01',
      review_dates: ['2027-04-01'],
    },
    runs: [],
    coverage: [],
    prospective_count: 0,
    retrospective_count: 1,
    non_event_count: 1,
    failure_count: 0,
    records: [
      {
        record_id: 'replay:AA',
        ticker: 'AA',
        session: '2026-09-28',
        run_id: 'replay',
        classification: 'retrospective',
        status: 'available',
        published_at: '2026-10-01T00:00:00Z',
        values: { dip_event_v1: false, dip_ready_v1: true, dip_component_count: 0 },
        code_revision: 'abc',
        config_hash: 'config',
        input_hash: 'input',
        retrieved_at: 'vintage',
        outcome: null,
      },
    ],
  },
} as unknown as Dashboard
it('does not mix replay with empty genuine prospective records', () => {
  render(<PaperArchive data={fixture} />)
  expect(
    screen.getByRole('heading', {
      name: 'Prospective archive initialized — awaiting first eligible completed session.',
    }),
  ).toBeInTheDocument()
  expect(screen.queryByRole('table', { name: 'Archived signal decisions' })).not.toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab', { name: 'Historical replay' }))
  expect(screen.getByRole('table', { name: 'Archived signal decisions' })).toHaveTextContent('AA')
  fireEvent.click(screen.getByRole('button', { name: 'AA' }))
  expect(screen.getByText('config', { exact: true })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('tab', { name: 'Prospective' }))
  expect(screen.queryByText('config', { exact: true })).not.toBeInTheDocument()
})
it('shows a short honest brief and reveals the unchanged full record only on request', async () => {
  render(<Experiments data={fixture} />)
  const brief = screen.getByRole('region', { name: 'EXP-002 short summary' })
  expect(brief).toHaveTextContent('required stock-breadth test failed')
  expect(brief.textContent!.split(/\s+/).length).toBeLessThan(110)
  expect(screen.queryByText('Registered breadth criterion failed.')).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('Full research record'))
  await waitFor(() =>
    expect(screen.getByText('Registered breadth criterion failed.')).toBeVisible(),
  )
  fireEvent.click(screen.getByRole('tab', { name: /EXP-001/ }))
  expect(screen.getByRole('region', { name: 'EXP-001 short summary' })).toHaveTextContent(
    'Some stocks lost money',
  )
  expect(screen.queryByText('Mixed results retained.')).not.toBeInTheDocument()
  fireEvent.click(screen.getByText('Full research record'))
  await waitFor(() => expect(screen.getByText('Mixed results retained.')).toBeVisible())
})
it('explains metrics on tap and labels numerical examples as examples', () => {
  render(<Help name="Win rate" />)
  const button = screen.getByRole('button', { name: 'Explain Win rate' })
  expect(button).toHaveAttribute('aria-expanded', 'false')
  fireEvent.click(button)
  expect(screen.getByRole('note')).toHaveTextContent(
    'Example only: 6 profitable trades out of 10 gives 60%',
  )
  expect(screen.getByRole('note')).toHaveTextContent(
    'Large losses can still make the overall result negative',
  )
  fireEvent.click(button)
  expect(screen.queryByRole('note')).not.toBeInTheDocument()
})
it('sorts and paginates a presentation copy without changing source returns', () => {
  const rows = [
    { ticker: 'BB', value: -0.1 },
    { ticker: 'AA', value: 0.2 },
    { ticker: 'CC', value: 0 },
  ]
  const copy = structuredClone(rows)
  render(
    <DataTable
      rows={rows}
      columns={[
        { key: 'ticker', label: 'Ticker' },
        { key: 'value', label: 'Mean', format: 'percent' },
      ]}
      caption="Test returns"
      pageSize={2}
    />,
  )
  fireEvent.click(screen.getByRole('button', { name: 'Mean' }))
  expect(
    within(screen.getByRole('table', { name: 'Test returns' })).getAllByRole('row')[1],
  ).toHaveTextContent('BB')
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
  expect(screen.getByRole('table')).toHaveTextContent('AA')
  expect(rows).toEqual(copy)
})
