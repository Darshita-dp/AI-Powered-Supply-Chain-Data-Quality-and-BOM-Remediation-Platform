import { NavLink, Outlet } from 'react-router-dom'

const LINKS = [
  { to: '/', label: 'Command Center' },
  { to: '/issues', label: 'Data Quality Explorer' },
  { to: '/parts', label: 'Part 360' },
  { to: '/bom', label: 'BOM Graph Explorer' },
  { to: '/workbench', label: 'Remediation Workbench' },
  { to: '/scenarios', label: 'Scenario Simulator' },
  { to: '/copilot', label: 'Steward Copilot' },
  { to: '/governance', label: 'AI Governance' },
]

export default function Layout() {
  return (
    <div className="app-shell">
      <aside className="sidenav">
        <div className="sidenav-brand">
          <h1>BOM Guardian AI</h1>
          <p>Supply chain data quality &amp; remediation</p>
        </div>
        <nav aria-label="Main">
          {LINKS.map((l) => (
            <NavLink key={l.to} to={l.to} end={l.to === '/'}>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidenav-footer">Synthetic data — portfolio project</div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
