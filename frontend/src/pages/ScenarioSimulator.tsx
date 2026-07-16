import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import {
  simulateFieldCorrection,
  simulateMerge,
  simulateReplacement,
} from '../api/endpoints'
import { ErrorState } from '../components/ui'
import type { Scenario } from '../types/api'

type Kind = 'merge' | 'field' | 'replace'

export default function ScenarioSimulator() {
  const [kind, setKind] = useState<Kind>('merge')
  const [a, setA] = useState('')
  const [b, setB] = useState('')
  const [c, setC] = useState('')
  const [result, setResult] = useState<Scenario | null>(null)

  const run = useMutation({
    mutationFn: (): Promise<Scenario> => {
      if (kind === 'merge') return simulateMerge(a, b)
      if (kind === 'field') return simulateFieldCorrection(a, b, c)
      return simulateReplacement(a, b, c)
    },
    onSuccess: setResult,
  })

  const fields: { label: string; value: string; set: (v: string) => void }[] =
    kind === 'merge'
      ? [
          { label: 'Duplicate part ID', value: a, set: setA },
          { label: 'Surviving part ID', value: b, set: setB },
        ]
      : kind === 'field'
        ? [
            { label: 'Part ID', value: a, set: setA },
            { label: 'Field (e.g. uom)', value: b, set: setB },
            { label: 'New value', value: c, set: setC },
          ]
        : [
            { label: 'Parent assembly ID', value: a, set: setA },
            { label: 'Old component ID', value: b, set: setB },
            { label: 'New component ID', value: c, set: setC },
          ]
  const ready = fields.every((f) => f.value.trim())

  return (
    <>
      <h2 className="page-title">Scenario Simulator</h2>
      <p className="page-subtitle">
        Preview a remediation before anyone approves it — baseline data is never modified
      </p>

      <div className="card">
        <div className="controls">
          <select aria-label="Scenario type" value={kind} onChange={(e) => { setKind(e.target.value as Kind); setResult(null) }}>
            <option value="merge">Duplicate merge</option>
            <option value="field">Field correction</option>
            <option value="replace">Component replacement</option>
          </select>
          {fields.map((f) => (
            <input
              key={f.label}
              aria-label={f.label}
              placeholder={f.label}
              value={f.value}
              onChange={(e) => f.set(e.target.value)}
            />
          ))}
          <button className="primary" disabled={!ready || run.isPending} onClick={() => run.mutate()}>
            {run.isPending ? 'Simulating…' : 'Simulate'}
          </button>
        </div>
        {run.isError && <ErrorState error={run.error} />}
      </div>

      {result && (
        <>
          <div className="grid-2">
            <div className="card">
              <h3>Before</h3>
              <pre className="mono" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                {JSON.stringify(result.before, null, 2)}
              </pre>
            </div>
            <div className="card">
              <h3>Proposed after-state</h3>
              <pre className="mono" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                {JSON.stringify(result.after, null, 2)}
              </pre>
            </div>
          </div>
          <div className="grid-2">
            <div className="card">
              <h3>Rules resolved</h3>
              {result.resolved_rules.length === 0 ? (
                <p style={{ color: 'var(--muted)', margin: 0 }}>None</p>
              ) : (
                <ul style={{ margin: 0, paddingLeft: 18 }}>
                  {result.resolved_rules.map((r) => <li key={r}><span className="badge ok">{r}</span></li>)}
                </ul>
              )}
            </div>
            <div className="card">
              <h3>New warnings</h3>
              {result.new_warnings.length === 0 ? (
                <p style={{ color: 'var(--muted)', margin: 0 }}>None — simulation is clean</p>
              ) : (
                <ul className="warning-list" style={{ margin: 0, paddingLeft: 18 }}>
                  {result.new_warnings.map((w, i) => <li key={i}>{w}</li>)}
                </ul>
              )}
            </div>
          </div>
          <p style={{ fontSize: 12, color: 'var(--muted)' }}>
            Scenario {result.scenario_id} persisted for audit. Applying any change still requires
            human approval in the Remediation Workbench.
          </p>
        </>
      )}
    </>
  )
}
