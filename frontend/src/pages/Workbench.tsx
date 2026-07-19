import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  approveIssue,
  fetchIssue,
  fetchIssueEvidence,
  fetchIssueHistory,
  fetchMe,
  generateRecommendation,
  rejectIssue,
} from '../api/endpoints'
import {
  EmptyState, ErrorState, Loading, SeverityBadge, StatusBadge,
} from '../components/ui'
import type { Proposal } from '../types/api'

export default function Workbench() {
  const { issueId } = useParams()
  if (!issueId) {
    return (
      <>
        <h2 className="page-title">Remediation Workbench</h2>
        <EmptyState>
          Open an issue from the <Link to="/issues">Data Quality Explorer</Link> to review and decide.
        </EmptyState>
      </>
    )
  }
  return <IssueDetail issueId={issueId} />
}

function IssueDetail({ issueId }: { issueId: string }) {
  const qc = useQueryClient()
  const [reason, setReason] = useState('')
  const [proposal, setProposal] = useState<Proposal | null>(null)

  // The decision is attributed to the authenticated principal server-side; the
  // client cannot supply a reviewer name.
  const me = useQuery({ queryKey: ['me'], queryFn: fetchMe })

  const issue = useQuery({ queryKey: ['issue', issueId], queryFn: () => fetchIssue(issueId) })
  const evidence = useQuery({
    queryKey: ['evidence', issueId],
    queryFn: () => fetchIssueEvidence(issueId),
  })
  const history = useQuery({
    queryKey: ['history', issueId],
    queryFn: () => fetchIssueHistory(issueId),
  })
  const recommend = useMutation({
    mutationFn: () => generateRecommendation(issueId),
    onSuccess: setProposal,
  })
  const decide = useMutation({
    mutationFn: ({ kind }: { kind: 'approve' | 'reject' }) =>
      kind === 'approve' ? approveIssue(issueId, reason) : rejectIssue(issueId, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['issue', issueId] })
      qc.invalidateQueries({ queryKey: ['history', issueId] })
    },
  })

  if (issue.isPending) return <Loading what="issue" />
  if (issue.isError) return <ErrorState error={issue.error} />
  const i = issue.data
  const decidable = !['APPROVED', 'REJECTED', 'CLOSED'].includes(i.status)

  return (
    <>
      <h2 className="page-title">Issue {i.issue_id}</h2>
      <p className="page-subtitle">
        {i.rule_id} · <SeverityBadge severity={i.severity} /> · <StatusBadge status={i.status} />
      </p>

      <div className="grid-2">
        <div>
          <div className="card">
            <h3>Summary</h3>
            <dl className="kv">
              <dt>Rule</dt><dd>{i.rule_id}</dd>
              <dt>Entity</dt><dd className="mono">{i.entity_type} / {i.entity_key}</dd>
              <dt>Field</dt><dd>{i.field ?? '—'}</dd>
              <dt>Domain</dt><dd>{i.domain.replaceAll('_', ' ')}</dd>
              <dt>Detected</dt><dd>{i.detected_at}</dd>
            </dl>
          </div>

          <div className="card">
            <h3>Evidence</h3>
            {evidence.isPending && <Loading what="evidence" />}
            {evidence.data && (
              <div className="table-wrap">
                <table className="data">
                  <thead><tr><th>Evidence</th><th>Field</th><th>Failed value</th></tr></thead>
                  <tbody>
                    {evidence.data.map((e) => (
                      <tr key={e.evidence_id}>
                        <td className="mono">{e.evidence_id.slice(0, 14)}…</td>
                        <td>{e.field ?? '—'}</td>
                        <td className="mono">{e.failed_value ?? 'NULL'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="card">
            <h3>Decision history</h3>
            {history.data && history.data.length === 0 && (
              <p style={{ color: 'var(--muted)', margin: 0 }}>No decisions yet.</p>
            )}
            {history.data && history.data.length > 0 && (
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {history.data.map((d) => (
                  <li key={d.decision_id}>
                    <strong>{d.decision}</strong> by {d.reviewer} — “{d.reason}”
                    <span style={{ color: 'var(--muted)' }}> ({d.before_status} → {d.after_status})</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        <div>
          <div className="card">
            <h3>AI recommendation</h3>
            {!proposal && (
              <button className="primary" onClick={() => recommend.mutate()} disabled={recommend.isPending}>
                {recommend.isPending ? 'Generating…' : 'Generate recommendation'}
              </button>
            )}
            {recommend.isError && <ErrorState error={recommend.error} />}
            {proposal && (
              <>
                <dl className="kv">
                  <dt>Action</dt><dd>{proposal.recommended_action.replaceAll('_', ' ')}</dd>
                  <dt>Confidence</dt><dd>{(proposal.confidence * 100).toFixed(0)}%</dd>
                  <dt>Provider</dt><dd>{proposal.provider} / {proposal.model}</dd>
                  <dt>Records affected</dt><dd className="mono">{proposal.records_affected.join(', ') || '—'}</dd>
                </dl>
                <p style={{ fontSize: 13 }}>{proposal.explanation}</p>
                {proposal.risks.length > 0 && (
                  <ul className="warning-list" style={{ fontSize: 12.5 }}>
                    {proposal.risks.map((r, idx) => <li key={idx}>{r}</li>)}
                  </ul>
                )}
              </>
            )}
          </div>

          <div className="card">
            <h3>Reviewer decision</h3>
            {!decidable && <p style={{ margin: 0, color: 'var(--muted)' }}>This issue has already been decided.</p>}
            {decidable && (
              <>
                <p className="signed-in-as" style={{ margin: '0 0 8px', color: 'var(--muted)' }}>
                  Signing as{' '}
                  <strong>{me.data ? `${me.data.username} (${me.data.role})` : '…'}</strong>
                  {' '}— recorded from your authenticated session, not typed in.
                </p>
                <textarea
                  aria-label="Reason"
                  placeholder="Decision rationale (required)"
                  rows={3}
                  style={{ width: '100%', marginBottom: 8 }}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                />
                <div className="controls">
                  <button
                    className="approve"
                    disabled={!reason || decide.isPending}
                    onClick={() => decide.mutate({ kind: 'approve' })}
                  >
                    Approve
                  </button>
                  <button
                    className="reject"
                    disabled={!reason || decide.isPending}
                    onClick={() => decide.mutate({ kind: 'reject' })}
                  >
                    Reject
                  </button>
                </div>
                {decide.isError && <ErrorState error={decide.error} />}
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
