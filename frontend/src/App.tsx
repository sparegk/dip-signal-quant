import { useEffect, useState } from 'react'
import { loadDashboard, type Dashboard, type Manifest } from './data'
import { Empty } from './components'
import Overview from './Overview'

export default function App() {
  const [loaded, setLoaded] = useState<{ manifest: Manifest; data: Dashboard } | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { const abort = new AbortController(); loadDashboard(abort.signal).then(setLoaded).catch(e => { if (e.name !== 'AbortError') setError(e.message) }); return () => abort.abort() }, [])
  return <div className="app-shell"><aside className="sidebar"><a className="brand" href="#overview"><span className="brand-mark">d/</span><div>DipSignal<small>RESEARCH TERMINAL</small></div></a><div className="nav-label">WORKSPACE</div><nav><a className="active" href="#overview"><span>01</span>Overview</a></nav><div className="sidebar-footer"><span className="status-dot" /> Frozen specification<p>Historical research.<br />No automated execution.</p><a href="https://github.com/sparegk/dip-signal-quant">Repository ↗</a></div></aside><div className="workspace"><header className="topbar"><span>DipSignal Research <span className="tag">V1 · Frozen</span></span><div><span>{loaded ? 'Local research export' : 'Data unavailable'}</span><span>Research update {loaded?.data.last_research_update || '—'}</span></div></header><main id="main">{error ? <Empty title="Local research data is not loaded">{error}<br /><code>python -m scripts.build_dashboard_data</code><br />Run from the repository root with the project environment, then reload this page.</Empty> : loaded ? <Overview data={loaded.data} /> : <p role="status" className="loading">Verifying local research export…</p>}</main><footer className="workspace-footer"><span>Research, not investment instructions.</span><span>{loaded ? `Export as of ${loaded.data.as_of}` : 'No sample data substituted'}</span></footer></div></div>
}
