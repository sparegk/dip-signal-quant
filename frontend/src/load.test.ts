import { webcrypto } from 'node:crypto'
import { afterEach, expect, it, vi } from 'vitest'
import { loadDashboard, loadSeries, readJSON, type Manifest } from './data'

afterEach(() => vi.unstubAllGlobals())
const bytes = (value: unknown) => new TextEncoder().encode(JSON.stringify(value))
const response = (value: unknown) => ({ ok: true, arrayBuffer: async () => bytes(value).buffer })
async function hash(value: unknown) {
  return [...new Uint8Array(await webcrypto.subtle.digest('SHA-256', bytes(value)))]
    .map((x) => x.toString(16).padStart(2, '0'))
    .join('')
}
it('loads the dashboard through a verified manifest and rejects altered content', async () => {
  vi.stubGlobal('crypto', webcrypto)
  const data = {
    schema_version: 1,
    experiments: [],
    archive: { prospective_count: 0 },
    exp002: { status: 'missing' },
  }
  const manifest = {
    schema_version: 1,
    dashboard: 'generations/example/dashboard.json',
    sha256: { 'dashboard.json': await hash(data) },
  }
  const fetch = vi
    .fn()
    .mockResolvedValueOnce(response(manifest))
    .mockResolvedValueOnce(response(data))
  vi.stubGlobal('fetch', fetch)
  expect((await loadDashboard()).data).toEqual(data)
  fetch
    .mockResolvedValueOnce(response(manifest))
    .mockResolvedValueOnce(response({ ...data, experiments: [{ id: 'altered' }] }))
  await expect(loadDashboard()).rejects.toThrow('integrity check failed')
})
it('handles missing exports and refuses unsafe paths without fetching them', async () => {
  const fetch = vi.fn().mockResolvedValue({ ok: false, status: 404 })
  vi.stubGlobal('fetch', fetch)
  await expect(readJSON('manifest.json')).rejects.toThrow('not found')
  await expect(readJSON('../config/private.json')).rejects.toThrow('Invalid export path')
  expect(fetch).toHaveBeenCalledTimes(1)
})
it('expands one ticker columnar file, verifies identity and preserves outcome separation', async () => {
  vi.stubGlobal('crypto', webcrypto)
  const payload = {
    schema_version: 1,
    ticker: 'AA',
    experiment: 'EXP-002',
    known_at_signal: { columns: ['date', 'dip_event_v1'], rows: [['2026-01-02', true]] },
    future_outcomes: { '2026-01-02': { horizons: [{ forward_return: -0.1 }] } },
  }
  const manifest = {
    series: { 'EXP-002/AA': 'series/AA.json' },
    sha256: { 'series/EXP-002/AA.json': await hash(payload) },
  } as unknown as Manifest
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(payload)))
  const result = await loadSeries(manifest, 'EXP-002', 'AA')
  expect(result.known_at_signal).toEqual([{ date: '2026-01-02', dip_event_v1: true }])
  expect(result.future_outcomes['2026-01-02'].horizons?.[0].forward_return).toBe(-0.1)
  await expect(loadSeries(manifest, 'EXP-002', 'BB')).rejects.toThrow('No preserved history')
  await expect(loadSeries({ ...manifest, sha256: {} }, 'EXP-002', 'AA')).rejects.toThrow(
    'integrity hash',
  )
  const invalid = { ...payload, ticker: 'BB' }
  manifest.sha256['series/EXP-002/AA.json'] = await hash(invalid)
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response(invalid)))
  await expect(loadSeries(manifest, 'EXP-002', 'AA')).rejects.toThrow('Invalid ticker export')
})
