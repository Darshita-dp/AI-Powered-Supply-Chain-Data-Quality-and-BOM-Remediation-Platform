/**
 * Thin typed fetch wrapper for the BOM Guardian API.
 * All requests go through the Vite dev proxy (`/api`) in development.
 */

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

/**
 * DEMONSTRATION authentication only. The API enforces role-based authorization;
 * the workbench signs in as a data steward via a demo bearer token so approval
 * actions are permitted. In a real deployment this would be an OIDC/SAML token
 * obtained from the corporate IdP, not a static value. Override with
 * VITE_DEMO_TOKEN (e.g. an analyst token for a read-only session).
 */
const DEMO_TOKEN = import.meta.env.VITE_DEMO_TOKEN ?? 'demo-steward-token'

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  return { Authorization: `Bearer ${DEMO_TOKEN}`, ...extra }
}

export async function apiGet<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(path, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v))
  }
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) throw new ApiError(res.status, `GET ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method: 'POST',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new ApiError(res.status, `POST ${path} failed: ${res.status}`)
  return res.json() as Promise<T>
}
