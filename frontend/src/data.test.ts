import { describe, expect, it } from 'vitest'
import { filterObservations, format } from './data'

describe('Research presentation contract', () => {
  it('formats fractions, differences and unavailable values consistently', () => {
    expect(format(0.01066)).toBe('+1.066%')
    expect(format(-0.00246)).toBe('-0.246%')
    expect(format(0.00244, 'pp')).toBe('+0.244 pp')
    expect(format(0)).toBe('0.000%')
    expect(format(0.6, 'rate')).toBe('60.000%')
    expect(format(null)).toBe('—')
    expect(format(Infinity)).toBe('—')
  })
  it('filters copies without altering chronology or source observations', () => {
    const rows = [
      {
        date: '2026-01-02',
        split: 'test',
        dip_component_count: 3,
        dip_event_v1: true,
        dip_condition_v1: true,
      },
      {
        date: '2026-01-05',
        split: 'test',
        dip_component_count: 4,
        dip_event_v1: false,
        dip_condition_v1: true,
      },
    ]
    const before = structuredClone(rows)
    const filters = {
      start: '2026-01-02',
      end: '2026-01-05',
      components: 'all',
      kind: 'event',
      split: 'test',
    }
    expect(filterObservations(rows, filters)).toHaveLength(1)
    expect(filterObservations(rows, { ...filters, kind: 'condition' })).toHaveLength(2)
    expect(filterObservations(rows, { ...filters, split: 'research' })).toHaveLength(0)
    expect(rows).toEqual(before)
  })
})
