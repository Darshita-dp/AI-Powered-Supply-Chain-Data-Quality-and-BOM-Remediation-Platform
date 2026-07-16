import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { apiPost } from '../api/client'
import { ErrorState } from '../components/ui'

interface CopilotResponse {
  question: string
  classification: string
  answer: string
  rows: Record<string, unknown>[]
  citations: string[]
  insufficient_evidence: boolean
  refused: boolean
}

const EXAMPLES = [
  'Why was PRT000123 marked as a duplicate?',
  'Which rules failed for PRT000123?',
  'Which obsolete components affect the most future demand?',
  'Which suppliers have the highest risk exposure?',
  'Show high-risk issues for PL01',
  'Why did the model abstain?',
]

export default function Copilot() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState<CopilotResponse[]>([])

  const ask = useMutation({
    mutationFn: (q: string) => apiPost<CopilotResponse>('/api/v1/copilot/query', { question: q }),
    onSuccess: (r) => setHistory((h) => [r, ...h]),
  })

  return (
    <>
      <h2 className="page-title">Data Steward Copilot</h2>
      <p className="page-subtitle">
        Read-only, evidence-grounded answers from governed data tools — it cannot approve
        or change anything
      </p>

      <div className="card">
        <form
          className="controls"
          onSubmit={(e) => {
            e.preventDefault()
            if (question.trim()) ask.mutate(question.trim())
          }}
        >
          <input
            aria-label="Question"
            placeholder="Ask about issues, duplicates, dependencies, exposure…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            style={{ flex: 1, minWidth: 280 }}
          />
          <button className="primary" type="submit" disabled={ask.isPending || !question.trim()}>
            {ask.isPending ? 'Thinking…' : 'Ask'}
          </button>
        </form>
        <div className="controls" style={{ marginBottom: 0 }}>
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" onClick={() => setQuestion(ex)} style={{ fontSize: 12 }}>
              {ex}
            </button>
          ))}
        </div>
        {ask.isError && <ErrorState error={ask.error} />}
      </div>

      {history.map((r, idx) => (
        <div className="card" key={idx}>
          <h3>{r.question}</h3>
          <p style={{ marginTop: 0 }}>
            {r.refused && <span className="badge critical" style={{ marginRight: 6 }}>refused</span>}
            {r.insufficient_evidence && (
              <span className="badge medium" style={{ marginRight: 6 }}>insufficient evidence</span>
            )}
            {r.answer}
          </p>
          {r.citations.length > 0 && (
            <p className="mono" style={{ fontSize: 11, color: 'var(--muted)', margin: 0 }}>
              Evidence: {r.citations.slice(0, 8).join(' · ')}
            </p>
          )}
        </div>
      ))}
    </>
  )
}
