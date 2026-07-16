import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchIssues } from '../api/endpoints'
import { EmptyState, ErrorState, Loading, SeverityBadge, StatusBadge } from '../components/ui'

const SEVERITIES = ['', 'critical', 'high', 'medium', 'low']
const DOMAINS = [
  '', 'completeness', 'uniqueness', 'validity', 'referential_integrity',
  'cross_field_consistency', 'temporal_consistency', 'anomaly', 'graph_integrity',
  'document_reconciliation',
]
const STATUSES = ['', 'DETECTED', 'PENDING_REVIEW', 'APPROVED', 'REJECTED']

export default function IssueExplorer() {
  const [page, setPage] = useState(1)
  const [severity, setSeverity] = useState('')
  const [domain, setDomain] = useState('')
  const [status, setStatus] = useState('')
  const [ruleId, setRuleId] = useState('')

  const params: Record<string, string | number> = { page, page_size: 20 }
  if (severity) params.severity = severity
  if (domain) params.domain = domain
  if (status) params.status = status
  if (ruleId) params.rule_id = ruleId

  const { data, isPending, isError, error } = useQuery({
    queryKey: ['issues', params],
    queryFn: () => fetchIssues(params),
  })

  return (
    <>
      <h2 className="page-title">Data Quality Explorer</h2>
      <p className="page-subtitle">Search and triage detected data-quality issues</p>

      <div className="controls">
        <select aria-label="Severity" value={severity} onChange={(e) => { setSeverity(e.target.value); setPage(1) }}>
          {SEVERITIES.map((s) => <option key={s} value={s}>{s || 'All severities'}</option>)}
        </select>
        <select aria-label="Domain" value={domain} onChange={(e) => { setDomain(e.target.value); setPage(1) }}>
          {DOMAINS.map((d) => <option key={d} value={d}>{d ? d.replaceAll('_', ' ') : 'All domains'}</option>)}
        </select>
        <select aria-label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
          {STATUSES.map((s) => <option key={s} value={s}>{s || 'All statuses'}</option>)}
        </select>
        <input
          aria-label="Rule ID"
          placeholder="Rule ID e.g. VALD-001"
          value={ruleId}
          onChange={(e) => { setRuleId(e.target.value.toUpperCase()); setPage(1) }}
        />
      </div>

      {isPending && <Loading what="issues" />}
      {isError && <ErrorState error={error} />}
      {data && data.items.length === 0 && <EmptyState>No issues match these filters.</EmptyState>}
      {data && data.items.length > 0 && (
        <>
          <div className="table-wrap card" style={{ padding: 0 }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Issue</th><th>Rule</th><th>Entity</th><th>Field</th>
                  <th>Severity</th><th>Domain</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((i) => (
                  <tr key={i.issue_id}>
                    <td><Link to={`/workbench/${i.issue_id}`}>{i.issue_id.slice(0, 12)}…</Link></td>
                    <td>{i.rule_id}</td>
                    <td className="mono">{i.entity_key}</td>
                    <td>{i.field ?? '—'}</td>
                    <td><SeverityBadge severity={i.severity} /></td>
                    <td>{i.domain.replaceAll('_', ' ')}</td>
                    <td><StatusBadge status={i.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pager">
            <button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
            <span>
              Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))} ({data.total} issues)
            </span>
            <button
              disabled={page >= Math.ceil(data.total / data.page_size)}
              onClick={() => setPage(page + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </>
  )
}
