export type JobType =
  | 'run_commands'
  | 'config_backup'
  | 'config_deploy_preview'
  | 'config_deploy_commit'
  | 'compliance_check'

export type JobStatus = 'queued' | 'scheduled' | 'running' | 'success' | 'partial' | 'failed' | 'cancelled'

export type JobLogLevel = 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'

/** Per-host result within a job */
export interface JobHostResult {
  status: JobStatus
  error?: string | null
  results?: Record<string, string> | null
  result?: string | null
  diff?: string | null
}

/** Summary of job results across all hosts */
export interface JobResultSummary {
  total?: number
  success?: number
  succeeded?: number
  failed?: number
  partial?: number
  running?: number
  queued?: number
  results?: Record<string, JobHostResult>
  diffs?: Record<string, JobHostResult>
}

/** Job payload for command jobs */
export interface JobPayload {
  commands?: string[]
  targets?: Record<string, string>
  [key: string]: unknown
}

export interface Job {
  id: number
  type: JobType
  status: JobStatus
  user_id: number | null
  user?: number | null
  customer_id?: number | null
  customer?: number | null
  requested_at: string
  scheduled_for?: string | null
  started_at?: string | null
  finished_at?: string | null
  completed_at?: string | null
  target_summary_json?: Record<string, unknown> | null
  result_summary_json?: JobResultSummary | string | null
  payload_json?: JobPayload | null
}

/** Normalized job with consistent field names */
export interface NormalizedJob extends Omit<Job, 'user' | 'customer' | 'completed_at'> {
  user_id: number | null
  customer_id: number | null
  started_at: string | null
  finished_at: string | null
}

export interface JobLog {
  id: number
  job_id: number
  ts: string
  level: JobLogLevel
  host?: string | null
  message: string
  extra_json?: Record<string, unknown> | null
}

/** Live log entry from WebSocket */
export interface LiveLogEntry {
  ts: string
  level: string
  message: string
  host?: string
}

export interface JobFilters {
  status?: string
  type?: string
  limit?: number
}

export interface JobCreateResponse {
  job_id: number
  status: string
}

export interface JobRetryResponse {
  job_id: number
  status: string
}
