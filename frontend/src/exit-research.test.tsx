import { fireEvent, render, screen } from '@testing-library/react'
import { expect, it } from 'vitest'
import ExitResearch from './ExitResearch'
import { Diagnosis, Hypotheses } from './Diagnosis'
import { format, type Dashboard } from './data'

const data = {
  exp002: { status: 'missing' },
  documents: {},
  archive: { prospective_count: 0 },
  hypotheses: [],
  exp004: {
    status: 'available',
    tables: {
      aggregate_summary: ['v1_control', 'training_selected', 'time_only'].map((policy, i) => ({
        policy,
        mode: 'independent',
        trade_count: 100,
        expected_value: 0.005 + i * 0.002,
        win_rate: 0.5,
        average_win: 0.05,
        average_loss: -0.05,
      })),
      fold_summary: ['v1_control', 'training_selected', 'time_only'].map((policy) => ({
        policy,
        mode: 'independent',
        fold: '2022',
        expected_value: -0.003,
      })),
      exit_efficiency: [],
      selected_policy_by_fold: [],
      ticker_summary: [],
    },
  },
} as unknown as Dashboard

it('loads EXP-004 with negative years and the time-only limitation visible', () => {
  render(<ExitResearch data={data} />)
  expect(screen.getByText('How Should We Exit a Dip?')).toBeInTheDocument()
  expect(screen.getByText(/holding for 10 bars had higher/)).toBeInTheDocument()
  expect(screen.getAllByText(format(-0.003)).length).toBe(3)
  expect(screen.getByText(/Prospective evaluation pending/)).toBeInTheDocument()
})
it('does not silently use same entries for non-overlapping policies', () => {
  render(<ExitResearch data={data} />)
  fireEvent.change(screen.getByLabelText('Analysis mode'), { target: { value: 'non_overlapping' } })
  expect(screen.getByText(/policies accept different subsets/)).toBeInTheDocument()
})
it('missing EXP-004 artifacts are explicit', () => {
  render(
    <ExitResearch
      data={{ ...data, exp004: { status: 'missing', reason: 'No verified exit artifacts' } }}
    />,
  )
  expect(screen.getByText('No verified exit artifacts')).toBeInTheDocument()
})
it('diagnosis missing data does not fabricate groups', () => {
  render(
    <Diagnosis data={{ ...data, diagnosis: { status: 'missing', reason: 'Diagnosis not run' } }} />,
  )
  expect(screen.getByText('Diagnosis not run')).toBeInTheDocument()
  expect(screen.getByText(/No group becomes a strategy/)).toBeInTheDocument()
})
it('hypotheses remain proposed and pending rather than strategies', () => {
  render(<Hypotheses data={data} />)
  expect(screen.getByText(/No new experiment or optimization/)).toBeInTheDocument()
  expect(screen.getByText('Hypothesis registry not exported yet.')).toBeInTheDocument()
})
