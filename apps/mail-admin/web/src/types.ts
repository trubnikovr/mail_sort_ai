export type JobStatus = 'pending' | 'processing' | 'completed' | 'review' | 'failed'

export interface JobSummary {
  id: string
  type: string
  status: JobStatus
  provider: string
  provider_message_id: string
  subject: string
  sender: string
  received_at: string | null
  created_at: string | null
  completed_at: string | null
  attempts: number
  max_attempts: number
  destination_id: string | null
  last_error: string | null
}

export interface DashboardSummary {
  jobs: Record<'total' | JobStatus, number>
  destinations: number
  pending_alerts: number
  recent_jobs: JobSummary[]
}

export interface JobDetail extends JobSummary {
  payload: Record<string, unknown>
  email: {
    subject: string
    sender: string
    headers: Record<string, string>
    body: string
    received_at: string | null
    expires_at: string | null
  } | null
  audit: { action: string; details: Record<string, unknown>; error: string | null; created_at: string }[]
}

export interface Destination {
  id: string
  account_id: string
  name: string
  description: string
  instruction: string
  mailbox: string
  is_active: boolean
  use_for_ai: boolean
}

export interface Page<T> {
  items: T[]
  limit: number
  offset: number
}

export interface ProcessingLog {
  id: string
  job_id: string
  created_at: string
  source: 'step' | 'ai' | 'audit'
  event: string
  status: string
  details: Record<string, unknown>
  error: string | null
  provider_message_id: string
  subject: string
}

export interface LogPage extends Page<ProcessingLog> {
  total: number
}

export interface DecisionSetting {
  key: 'mail_decision.enabled'
  value: boolean
  description: string
  updated_at: string | null
}

export interface ManagedServiceStatus {
  status: 'starting' | 'running' | 'restarting'
  pid: number | null
  restart_count: number
  last_exit_code: number | null
}

export interface ServicesHealth {
  status: 'ready' | 'degraded' | 'unavailable'
  services: Partial<Record<'mail-collector' | 'mail-decision' | 'mail-router', ManagedServiceStatus>>
}

export interface AuthStatus {
  authenticated: boolean
  username?: string
}
