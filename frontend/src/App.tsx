import { lazy, Suspense, useEffect, useState } from 'react'
import { loadDashboard, type Dashboard, type Manifest } from './data'
import { Empty } from './components'
import Overview from './Overview'
const Research = lazy(() => import('./ResearchRouter'))
const Explorer = lazy(() => import('./Explorer'))
const pages = [
  'Overview',
  'Signals',
  'Signal Explorer',
  'Experiments',
  'Robustness',
  'Backtest',
  'Features',
  'Paper Archive',
  'Data Quality',
  'Research Log',
  'Roadmap',
]
const slug = (name: string) => name.toLowerCase().replaceAll(' ', '-')

export default function App() {
  const [loaded, setLoaded] = useState<{ manifest: Manifest; data: Dashboard } | null>(null)
  const [error, setError] = useState('')
  const [route, setRoute] = useState(location.hash.slice(1) || 'overview')
  const [menu, setMenu] = useState(false)
  useEffect(() => {
    const change = () => {
      setRoute(location.hash.slice(1) || 'overview')
      setMenu(false)
      window.scrollTo(0, 0)
    }
    window.addEventListener('hashchange', change)
    return () => window.removeEventListener('hashchange', change)
  }, [])
  useEffect(() => {
    const abort = new AbortController()
    loadDashboard(abort.signal)
      .then(setLoaded)
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message)
      })
    return () => abort.abort()
  }, [])
  const [page, query = ''] = route.split('?')
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main"
        onClick={(event) => {
          event.preventDefault()
          document.getElementById('main')?.focus()
        }}
      >
        Skip to content
      </a>
      <aside className={`sidebar ${menu ? 'is-open' : ''}`} id="navigation">
        <a className="brand" href="#overview">
          <span className="brand-mark">d/</span>
          <div>
            DipSignal<small>RESEARCH TERMINAL</small>
          </div>
        </a>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Research workspace">
          {pages.map((name, i) => (
            <a
              key={name}
              className={page === slug(name) ? 'active' : ''}
              aria-current={page === slug(name) ? 'page' : undefined}
              href={`#${slug(name)}`}
            >
              <span>{String(i + 1).padStart(2, '0')}</span>
              {name}
            </a>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot" /> Frozen specification
          <p>
            Historical research.
            <br />
            No automated execution.
          </p>
          <a href="https://github.com/sparegk/dip-signal-quant">Repository ↗</a>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <button
            className="menu-toggle"
            aria-expanded={menu}
            aria-controls="navigation"
            onClick={() => setMenu(!menu)}
          >
            Menu
          </button>
          <span>
            DipSignal Research <span className="tag">V1 · Frozen</span>
          </span>
          <div>
            <span>{loaded ? 'Local research export' : 'Data unavailable'}</span>
            <span>Research update {loaded?.data.last_research_update || '—'}</span>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          {error ? (
            <Empty title="Local research data is not loaded">
              {error}
              <br />
              <code>python -m scripts.build_dashboard_data</code>
              <br />
              Run from the repository root with the project environment, then reload this page.
            </Empty>
          ) : loaded ? (
            <Suspense fallback={<p role="status">Loading research view…</p>}>
              {page === 'overview' ? (
                <Overview data={loaded.data} />
              ) : page === 'signal-explorer' || page === 'features' ? (
                <Explorer
                  key={route}
                  data={loaded.data}
                  manifest={loaded.manifest}
                  featureMode={page === 'features'}
                  query={query}
                />
              ) : (
                <Research page={page} data={loaded.data} />
              )}
            </Suspense>
          ) : (
            <p role="status" className="loading">
              Verifying local research export…
            </p>
          )}
        </main>
        <footer className="workspace-footer">
          <span>Research, not investment instructions.</span>
          <span>{loaded ? `Export as of ${loaded.data.as_of}` : 'No sample data substituted'}</span>
        </footer>
      </div>
    </div>
  )
}
