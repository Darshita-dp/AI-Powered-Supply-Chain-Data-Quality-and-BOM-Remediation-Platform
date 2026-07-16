import './App.css'

/**
 * Application shell. Pages (Command Center, DQ Explorer, Issue Detail, Part 360,
 * BOM Graph Explorer, Remediation Workbench, Scenario Simulator, AI Governance)
 * are added in M16 once the backend API exists — no mock-data pages before then.
 */
function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>BOM Guardian AI</h1>
        <p className="app-tagline">Supply chain data quality &amp; BOM remediation</p>
      </header>
      <main className="app-main">
        <p>
          Backend not yet connected. The remediation workbench is built in milestone M16
          against the live API.
        </p>
      </main>
    </div>
  )
}

export default App
