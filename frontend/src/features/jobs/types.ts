// Re-export job types from central types
export type {
  Job,
  JobType,
  JobStatus,
  JobLog,
  JobLogLevel,
  JobHostResult,
  JobResultSummary,
  JobPayload,
  NormalizedJob,
  LiveLogEntry,
  JobFilters,
  JobCreateResponse,
  JobRetryResponse,
} from '@/types/job'

/** Host counts summary for job results */
export interface HostCounts {
  success: number
  failed: number
  partial: number
  queued: number
  running: number
  total: number
}
