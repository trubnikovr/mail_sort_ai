import type { AuthStatus, DashboardSummary, DecisionSetting, Destination, JobDetail, JobSummary, LogPage, Page, ServicesHealth } from '../types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Accept', 'application/json')
  const response = await fetch(path, { ...init, headers, credentials: 'same-origin' })
  if (!response.ok) {
    if (response.status === 401 && !path.endsWith('/auth/login') && !path.endsWith('/auth/me')) {
      window.dispatchEvent(new Event('mail-admin:unauthorized'))
    }
    const payload = await response.json().catch(() => null) as { detail?: string } | null
    throw new Error(`${response.status}:${payload?.detail || response.statusText || 'Request failed'}`)
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const api = {
  auth: () => request<AuthStatus>('/api/auth/me'),
  login: (username: string, password: string) => request<AuthStatus>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  }),
  logout: () => request<void>('/api/auth/logout', { method: 'POST' }),
  dashboard: () => request<DashboardSummary>('/api/dashboard/summary'),
  jobs: (q: string, status: string, offset = 0) => {
    const params = new URLSearchParams({ q, status, limit: '25', offset: String(offset) })
    return request<Page<JobSummary>>(`/api/jobs?${params}`)
  },
  job: (id: string) => request<JobDetail>(`/api/jobs/${id}`),
  logs: (q: string, offset = 0) => {
    const params = new URLSearchParams({ q, limit: '50', offset: String(offset) })
    return request<LogPage>(`/api/logs?${params}`)
  },
  settings: () => request<DecisionSetting>('/api/settings'),
  services: () => request<ServicesHealth>('/api/services'),
  setDecisionEnabled: (value: boolean) => request<DecisionSetting>('/api/settings/mail_decision.enabled', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  }),
  destinations: () => request<Destination[]>('/api/destinations'),
  createDestination: (destination: Omit<Destination, 'id'> & { id: string }) => request<Destination>('/api/destinations', {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(destination),
  }),
  updateDestination: (id: string, destination: Omit<Destination, 'id'> & { id: string }) => request<Destination>(`/api/destinations/${encodeURIComponent(id)}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(destination),
  }),
  deleteDestination: (id: string) => request<void>(`/api/destinations/${encodeURIComponent(id)}`, { method: 'DELETE' }),
}
