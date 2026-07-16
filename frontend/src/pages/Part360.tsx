import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  fetchIssues,
  fetchPartImpact,
  fetchPartLineage,
  fetchParts,
} from '../api/endpoints'
import {
  EmptyState, ErrorState, Loading, Money, Num, SeverityBadge,
} from '../components/ui'

export default function Part360() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<string | null>(null)

  const parts = useQuery({
    queryKey: ['parts', search, page],
    queryFn: () => fetchParts({ page, page_size: 12, ...(search ? { search } : {}) }),
  })
  const lineage = useQuery({
    queryKey: ['lineage', selected],
    queryFn: () => fetchPartLineage(selected!),
    enabled: !!selected,
  })
  const impact = useQuery({
    queryKey: ['impact', selected],
    queryFn: () => fetchPartImpact(selected!),
    enabled: !!selected,
  })
  const partIssues = useQuery({
    queryKey: ['issues', 'part', selected],
    queryFn: () => fetchIssues({ entity_key: selected!, page_size: 20 }),
    enabled: !!selected,
  })

  return (
    <>
      <h2 className="page-title">Part 360</h2>
      <p className="page-subtitle">Golden record, lineage, exposure and issues for one part</p>

      <div className="controls">
        <input
          aria-label="Search parts"
          placeholder="Search part number or description…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1) }}
          style={{ width: 320 }}
        />
      </div>

      <div className="grid-2">
        <div>
          {parts.isPending && <Loading what="parts" />}
          {parts.isError && <ErrorState error={parts.error} />}
          {parts.data && (
            <>
              <div className="table-wrap card" style={{ padding: 0 }}>
                <table className="data">
                  <thead>
                    <tr><th>Part</th><th>Description</th><th>Status</th><th>Cost</th></tr>
                  </thead>
                  <tbody>
                    {parts.data.items.map((p) => (
                      <tr
                        key={p.part_key}
                        onClick={() => setSelected(p.part_key)}
                        style={{ cursor: 'pointer', background: selected === p.part_key ? '#eff6ff' : undefined }}
                      >
                        <td className="mono">{p.source_part_number ?? p.part_key}</td>
                        <td>{p.description ?? <em style={{ color: 'var(--critical)' }}>missing</em>}</td>
                        <td>{p.lifecycle_status}</td>
                        <td>{p.standard_cost?.toFixed(2) ?? '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pager">
                <button disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
                <span>Page {page} ({parts.data.total} parts)</span>
                <button
                  disabled={page >= Math.ceil(parts.data.total / parts.data.page_size)}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </button>
              </div>
            </>
          )}
        </div>

        <div>
          {!selected && <EmptyState>Select a part to see its 360° view.</EmptyState>}
          {selected && (
            <>
              {impact.data && (
                <div className="card">
                  <h3>Blast radius — {selected}</h3>
                  <div className="stat-grid">
                    <div className="stat"><div className="label">Assemblies affected</div><div className="value"><Num value={impact.data.affected_parent_assemblies} /></div></div>
                    <div className="stat"><div className="label">Demand exposed</div><div className="value"><Num value={impact.data.future_demand_qty_exposed} /></div></div>
                    <div className="stat"><div className="label">Inventory exposed</div><div className="value"><Money value={impact.data.inventory_value_exposed} /></div></div>
                    <div className="stat"><div className="label">Priority</div><div className="value">{impact.data.operational_priority}</div></div>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--muted)', margin: 0 }}>
                    Explore usage in the <Link to={`/bom?part=${selected}`}>BOM Graph Explorer</Link>.
                  </p>
                </div>
              )}
              {lineage.isPending && <Loading what="lineage" />}
              {lineage.data && (
                <div className="card">
                  <h3>Golden record (field-level lineage)</h3>
                  <div className="table-wrap">
                    <table className="data">
                      <thead>
                        <tr><th>Field</th><th>Value</th><th>Source</th><th>Confidence</th></tr>
                      </thead>
                      <tbody>
                        {Object.entries(lineage.data.fields).map(([field, d]) => (
                          <tr key={field} title={d.reason}>
                            <td>{field}</td>
                            <td>{String(d.selected_value)}</td>
                            <td>{d.source_system}</td>
                            <td>{(d.confidence * 100).toFixed(0)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p style={{ fontSize: 12, color: 'var(--muted)' }}>
                    Cluster members: {lineage.data.members.join(', ')}
                  </p>
                </div>
              )}
              {partIssues.data && partIssues.data.items.length > 0 && (
                <div className="card">
                  <h3>Open issues on this part</h3>
                  <ul style={{ margin: 0, paddingLeft: 18 }}>
                    {partIssues.data.items.map((i) => (
                      <li key={i.issue_id}>
                        <Link to={`/workbench/${i.issue_id}`}>{i.rule_id}</Link>{' '}
                        <SeverityBadge severity={i.severity} />
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  )
}
