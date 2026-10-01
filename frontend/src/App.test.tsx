import { render, screen, waitFor } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import App from './App'
import * as data from './data'

it('shows honest setup instructions when the export is missing', async () => {
  vi.spyOn(data, 'loadDashboard').mockRejectedValue(new Error('Research export not found.'))
  render(<App />)
  await waitFor(() =>
    expect(screen.getByText('Local research data is not loaded')).toBeInTheDocument(),
  )
  expect(screen.getByText('python -m scripts.build_dashboard_data')).toBeInTheDocument()
  expect(screen.queryByText('winning strategy')).not.toBeInTheDocument()
})
