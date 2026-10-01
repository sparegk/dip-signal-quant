import type { Dashboard } from './data'
import { Backtest, ResearchLog, Roadmap, Robustness } from './Research'
import Experiments from './ExperimentPage'
import { DataQuality, PaperArchive } from './Preservation'
import { Signals } from './Explorer'
import { Empty } from './components'
export default function ResearchRouter({ page, data }: { page: string; data: Dashboard }) {
  switch (page) {
    case 'signals':
      return <Signals data={data} />
    case 'experiments':
      return <Experiments data={data} />
    case 'robustness':
      return <Robustness data={data} />
    case 'backtest':
      return <Backtest data={data} />
    case 'paper-archive':
      return <PaperArchive data={data} />
    case 'data-quality':
      return <DataQuality data={data} />
    case 'research-log':
      return <ResearchLog data={data} />
    case 'roadmap':
      return <Roadmap data={data} />
    default:
      return (
        <Empty title="View not found">
          <a href="#overview">Return to Overview</a>
        </Empty>
      )
  }
}
