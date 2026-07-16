import { useQuery } from '@tanstack/react-query'
import cytoscape from 'cytoscape'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { fetchBomGraph, fetchReverseDeps } from '../api/endpoints'
import { EmptyState, ErrorState, Loading } from '../components/ui'
import type { BomGraphData } from '../types/api'

function nodeColor(n: BomGraphData['nodes'][number], root: string): string {
  if (n.in_cycle) return '#db2777'
  if (n.id === root) return '#1d4ed8'
  if (n.lifecycle_status === 'OBSOLETE') return '#b91c1c'
  if (n.lifecycle_status === 'BLOCKED') return '#c2410c'
  return '#64748b'
}

function GraphCanvas({ data }: { data: BomGraphData }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const cy = cytoscape({
      container: ref.current,
      elements: [
        ...data.nodes.map((n) => ({
          data: { id: n.id, label: n.id, color: nodeColor(n, data.root) },
        })),
        ...data.edges.map((e) => ({
          data: {
            id: `${e.parent}->${e.child}`,
            source: e.parent,
            target: e.child,
            qty: e.quantity_per ?? '',
          },
        })),
      ],
      style: [
        {
          selector: 'node',
          style: {
            'background-color': 'data(color)',
            label: 'data(label)',
            'font-size': 9,
            color: '#1f2937',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            width: 22,
            height: 22,
          },
        },
        {
          selector: 'edge',
          style: {
            width: 1.5,
            'line-color': '#cbd5e1',
            'target-arrow-color': '#cbd5e1',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
            label: 'data(qty)',
            'font-size': 8,
            color: '#94a3b8',
          },
        },
      ],
      layout: { name: 'breadthfirst', directed: true, spacingFactor: 1.2, roots: [data.root] },
    })
    return () => cy.destroy()
  }, [data])
  return <div ref={ref} className="graph-box" role="img" aria-label="BOM graph" />
}

export default function BomExplorer() {
  const [searchParams] = useSearchParams()
  const [partId, setPartId] = useState(searchParams.get('part') ?? '')
  const [depth, setDepth] = useState(3)
  const [submitted, setSubmitted] = useState(searchParams.get('part') ?? '')

  const graph = useQuery({
    queryKey: ['bom', submitted, depth],
    queryFn: () => fetchBomGraph(submitted, depth),
    enabled: !!submitted,
    retry: false,
  })
  const reverse = useQuery({
    queryKey: ['bom-reverse', submitted],
    queryFn: () => fetchReverseDeps(submitted),
    enabled: !!submitted,
    retry: false,
  })

  return (
    <>
      <h2 className="page-title">BOM Graph Explorer</h2>
      <p className="page-subtitle">Interactive dependency graph with cycle and lifecycle highlighting</p>

      <form
        className="controls"
        onSubmit={(e) => {
          e.preventDefault()
          setSubmitted(partId.trim())
        }}
      >
        <input
          aria-label="Part ID"
          placeholder="Part ID e.g. PRT000123"
          value={partId}
          onChange={(e) => setPartId(e.target.value)}
          style={{ width: 240 }}
        />
        <label>
          Depth{' '}
          <select value={depth} onChange={(e) => setDepth(Number(e.target.value))} aria-label="Depth">
            {[1, 2, 3, 5, 8].map((d) => <option key={d} value={d}>{d}</option>)}
          </select>
        </label>
        <button className="primary" type="submit">Explore</button>
      </form>

      {!submitted && <EmptyState>Enter a part ID to explore its BOM structure.</EmptyState>}
      {graph.isPending && submitted && <Loading what="graph" />}
      {graph.isError && <ErrorState error={graph.error} />}
      {graph.data && (
        <>
          <GraphCanvas data={graph.data} />
          <div className="legend">
            <span className="l-root">root</span>
            <span className="l-active">active component</span>
            <span className="l-obsolete">obsolete</span>
            <span className="l-blocked">blocked</span>
            <span className="l-cycle">in cycle</span>
          </div>
          {graph.data.cycles.length > 0 && (
            <div className="card" style={{ marginTop: 12 }}>
              <h3>Cycles detected</h3>
              <ul className="warning-list">
                {graph.data.cycles.map((c, i) => <li key={i} className="mono">{c.join(' → ')}</li>)}
              </ul>
            </div>
          )}
          {reverse.data && (
            <div className="card" style={{ marginTop: 12 }}>
              <h3>Reverse dependencies ({reverse.data.affected_assembly_count} assemblies affected)</h3>
              <p className="mono" style={{ margin: 0, fontSize: 12 }}>
                {reverse.data.reverse_dependencies.join(', ') || 'none — top-level assembly'}
              </p>
            </div>
          )}
        </>
      )}
    </>
  )
}
