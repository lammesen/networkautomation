export type JobType =
  | 'run_commands'
  | 'config_backup'
  | 'config_deploy_preview'
  | 'config_deploy_commit'
  | 'compliance_check'

export type JobStatus = 'queued' | 'scheduled' | 'running' | 'success' | 'partial' | 'failed'

export interface Job {
  id: number
  type: JobType
  status: JobStatus
  user_id: number
  customer_id?: number
  requested_at: string
  scheduled_for?: string | null
  started_at?: string | null
  finished_at?: string | null
  target_summary_json?: Record<string, unknown> | null
  result_summary_json?: Record<string, unknown> | null
  payload_json?: Record<string, unknown> | null
}

export interface JobLog {
  id: number
  job_id: number
  ts: string
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG'
  host?: string | null
  message: string
  extra_json?: Record<string, unknown> | null
}

export interface JobCreateResponse {
  job_id: number
  status: string
}

export interface JobRetryResponse {
  job_id: number
  status: string
}
