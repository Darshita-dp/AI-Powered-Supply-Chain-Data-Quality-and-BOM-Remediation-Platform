import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  fetchBusinessImpact,
  fetchIssues,
  fetchQualityAnalytics,
  fetchRemediationAnalytics,
} from '../api/endpoints'
import { ErrorState, Loading, Money, Num, SeverityBadge, Stat } from '../components/ui'

export default function CommandCenter() {
  const quality = useQuery({ queryKey: ['analytics', 'quality'], queryFn: fetchQualityAnalytics })
  const impact = useQuery({ queryKey: ['analytics', 'impact'], queryFn: fetchBusinessImpact })
  const remediation = useQuery({
    queryKey: ['analytics', 'remediation'],
    queryFn: fetchRemediationAnalytics,
  })
  const topIssues = useQuery({
    queryKey: ['issues', 'top'],
    queryFn: () => fetchIssues({ page_size: 8, severity: 'critical', status: 'DETECTED' }),
  })

  if (quality.isPending || impact.isPending || remediation.isPending) return <Loading what="command center" />
  if (quality.isError) return <ErrorState error={quality.error} />
  if (impact.isError) return <ErrorState error={impact.error} />
  if (remediation.isError) return <ErrorState error={remediation.error} />

  const q = quality.data
  const b = impact.data
  const r = remediation.data
  return (
    <>
      <h2 className="page-title">Command Center</h2>
      <p className="page-subtitle">Enterprise data-quality posture across all source systems</p>

      <div className="stat-grid">
        <Stat label="Enterprise quality score" value={q.enterprise_quality_score.toFixed(1)} />
        <Stat label="Open issues" value={<Num value={q.open_issues} />} />
        <Stat
          label="Critical open"
          value={<Num value={q.open_by_severity['critical'] ?? 0} />}
        />
        <Stat label="Inventory exposure" value={<Money value={b.total_inventory_value} />} />
        <Stat label="Future demand (qty)" value={<Num value={b.total_future_demand_qty} />} />
        <Stat label="Entities w/ critical issues" value={<Num value={b.entities_with_critical_issues} />} />
        <Stat label="Remediation backlog" value={<Num value={r.backlog} />} />
        <Stat
          label="Acceptance rate"
          value={r.acceptance_rate === null ? '—' : `${(r.acceptance_rate * 100).toFixed(0)}%`}
        />
      </div>

      <div className="grid-2">
        <div className="card">
          <h3>Open issues by domain</h3>
          <div className="table-wrap">
            <table className="data">
              <tbody>
                {Object.entries(q.open_by_domain).map(([domain, n]) => (
                  <tr key={domain}>
                    <td>{domain.replaceAll('_', ' ')}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h3>Top priorities (critical, unreviewed)</h3>
          {topIssues.isPending && <Loading what="issues" />}
          {topIssues.data && topIssues.data.items.length === 0 && (
            <p style={{ color: 'var(--muted)' }}>No critical issues awaiting review.</p>
          )}
          {topIssues.data && topIssues.data.items.length > 0 && (
            <div className="table-wrap">
              <table className="data">
                <tbody>
                  {topIssues.data.items.map((i) => (
                    <tr key={i.issue_id}>
                      <td>
                        <Link to={`/workbench/${i.issue_id}`}>{i.rule_id}</Link>
                      </td>
                      <td className="mono">{i.entity_key}</td>
                      <td>
                        <SeverityBadge severity={i.severity} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
