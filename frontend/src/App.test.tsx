import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

function renderAt(path: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

function mockFetch(payloads: Record<string, unknown>) {
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input)
      const key = Object.keys(payloads).find((k) => url.includes(k))
      if (!key) return new Response('{}', { status: 404 })
      return new Response(JSON.stringify(payloads[key]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    }),
  )
}

afterEach(() => vi.unstubAllGlobals())

describe('App shell', () => {
  it('renders navigation with all eight destinations', () => {
    mockFetch({})
    renderAt('/issues')
    for (const label of [
      'Command Center', 'Data Quality Explorer', 'Part 360', 'BOM Graph Explorer',
      'Remediation Workbench', 'Scenario Simulator', 'AI Governance',
    ]) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument()
    }
  })
})

describe('Command Center', () => {
  it('renders KPIs from the API', async () => {
    mockFetch({
      '/analytics/quality': {
        enterprise_quality_score: 87.3, weighted_issue_points: 120, open_issues: 42,
        parts_in_scope: 900, open_by_severity: { critical: 5 }, open_by_domain: { validity: 10 },
        top_rules: [],
      },
      '/analytics/business-impact': {
        total_inventory_value: 125000, total_future_demand_qty: 5400,
        entities_with_critical_issues: 7,
      },
      '/analytics/remediation': { decisions: {}, acceptance_rate: null, backlog: 12 },
      '/issues': { items: [], total: 0, page: 1, page_size: 8 },
    })
    renderAt('/')
    await waitFor(() => expect(screen.getByText('87.3')).toBeInTheDocument())
    expect(screen.getByText('Enterprise quality score')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })
})

describe('Issue Explorer', () => {
  it('lists issues and shows severity badges', async () => {
    mockFetch({
      '/issues': {
        items: [
          {
            issue_id: 'ISS-abcdef123456', rule_id: 'VALD-001', entity_type: 'part',
            entity_key: 'PRT000042', field: 'uom', severity: 'high', domain: 'validity',
            status: 'DETECTED', detected_at: '2026-07-16',
          },
        ],
        total: 1, page: 1, page_size: 20,
      },
    })
    renderAt('/issues')
    await waitFor(() => expect(screen.getByText('VALD-001')).toBeInTheDocument())
    expect(screen.getAllByText('high').length).toBeGreaterThan(0)
    expect(screen.getByText('PRT000042')).toBeInTheDocument()
  })

  it('shows the empty state when no issues match', async () => {
    mockFetch({ '/issues': { items: [], total: 0, page: 1, page_size: 20 } })
    renderAt('/issues')
    await waitFor(() =>
      expect(screen.getByText(/No issues match these filters/)).toBeInTheDocument(),
    )
  })
})

describe('Scenario Simulator', () => {
  it('disables simulate until inputs are filled', () => {
    mockFetch({})
    renderAt('/scenarios')
    expect(screen.getByRole('button', { name: 'Simulate' })).toBeDisabled()
  })
})
