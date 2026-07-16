import { useQuery } from '@tanstack/react-query'
import { fetchAIGovernance, fetchRemediationAnalytics } from '../api/endpoints'
import { EmptyState, ErrorState, Loading, Num, Stat } from '../components/ui'

export default function Governance() {
  const gov = useQuery({ queryKey: ['analytics', 'ai'], queryFn: fetchAIGovernance })
  const remediation = useQuery({
    queryKey: ['analytics', 'remediation'],
    queryFn: fetchRemediationAnalytics,
  })

  if (gov.isPending || remediation.isPending) return <Loading what="governance metrics" />
  if (gov.isError) return <ErrorState error={gov.error} />
  if (remediation.isError) return <ErrorState error={remediation.error} />

  const g = gov.data
  const r = remediation.data
  if (g.calls === 0) {
    return (
      <>
        <h2 className="page-title">AI Governance</h2>
        <EmptyState>
          No AI calls recorded yet. Generate a recommendation in the Remediation Workbench first.
        </EmptyState>
      </>
    )
  }

  return (
    <>
      <h2 className="page-title">AI Governance</h2>
      <p className="page-subtitle">Every AI call is audited: provider, model, prompt version, validation</p>

      <div className="stat-grid">
        <Stat label="Total AI calls" value={<Num value={g.calls} />} />
        <Stat label="Abstention rate" value={`${((g.abstention_rate ?? 0) * 100).toFixed(1)}%`} />
        <Stat label="Validation failures" value={`${((g.validation_failure_rate ?? 0) * 100).toFixed(1)}%`} />
        <Stat label="Avg latency" value={`${g.avg_latency_ms ?? 0} ms`} />
        <Stat label="Avg confidence" value={`${(((g.avg_confidence ?? 0)) * 100).toFixed(0)}%`} />
        <Stat
          label="Acceptance rate"
          value={r.acceptance_rate === null ? '—' : `${(r.acceptance_rate * 100).toFixed(0)}%`}
        />
      </div>

      <div className="grid-2">
        <div className="card">
          <h3>Calls by provider</h3>
          <div className="table-wrap">
            <table className="data">
              <tbody>
                {Object.entries(g.by_provider ?? {}).map(([provider, n]) => (
                  <tr key={provider}>
                    <td>{provider}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h3>Prompt versions in use</h3>
          <p className="mono" style={{ margin: 0 }}>{(g.prompt_versions ?? []).join(', ')}</p>
          <h3 style={{ marginTop: 16 }}>Reviewer decisions</h3>
          <div className="table-wrap">
            <table className="data">
              <tbody>
                {Object.entries(r.decisions).map(([decision, n]) => (
                  <tr key={decision}>
                    <td>{decision}</td>
                    <td style={{ textAlign: 'right', fontWeight: 600 }}>{n}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  )
}
