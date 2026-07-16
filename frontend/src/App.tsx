import { Route, Routes } from 'react-router-dom'
import './App.css'
import Layout from './components/Layout'
import BomExplorer from './pages/BomExplorer'
import CommandCenter from './pages/CommandCenter'
import Copilot from './pages/Copilot'
import Governance from './pages/Governance'
import IssueExplorer from './pages/IssueExplorer'
import Part360 from './pages/Part360'
import ScenarioSimulator from './pages/ScenarioSimulator'
import Workbench from './pages/Workbench'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<CommandCenter />} />
        <Route path="issues" element={<IssueExplorer />} />
        <Route path="parts" element={<Part360 />} />
        <Route path="bom" element={<BomExplorer />} />
        <Route path="workbench" element={<Workbench />} />
        <Route path="workbench/:issueId" element={<Workbench />} />
        <Route path="scenarios" element={<ScenarioSimulator />} />
        <Route path="copilot" element={<Copilot />} />
        <Route path="governance" element={<Governance />} />
      </Route>
    </Routes>
  )
}
