import type { ReactNode } from 'react'

export function Loading({ what = 'data' }: { what?: string }) {
  return <div className="state" role="status">Loading {what}…</div>
}

export function ErrorState({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : 'Something went wrong'
  return (
    <div className="state error" role="alert">
      {message}
    </div>
  )
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="state">{children}</div>
}

export function SeverityBadge({ severity }: { severity: string }) {
  return <span className={`badge ${severity}`}>{severity}</span>
}

export function StatusBadge({ status }: { status: string }) {
  const cls = status === 'APPROVED' ? 'ok' : 'status'
  return <span className={`badge ${cls}`}>{status}</span>
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  )
}

export function Money({ value }: { value: number }) {
  return <>{value.toLocaleString(undefined, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })}</>
}

export function Num({ value }: { value: number }) {
  return <>{value.toLocaleString()}</>
}
