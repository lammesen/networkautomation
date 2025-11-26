import type { Job, NormalizedJob, JobResultSummary, JobHostResult } from '@/types/job'

/**
 * Normalize job fields to handle API inconsistencies
 * Some endpoints return user/customer as ID directly, others as user_id/customer_id
 */
export function normalizeJob(job: Job): NormalizedJob {
  return {
    ...job,
    customer_id: job.customer_id ?? job.customer ?? null,
    user_id: job.user_id ?? job.user ?? null,
    started_at: job.started_at ?? job.requested_at ?? null,
    finished_at: job.finished_at ?? job.completed_at ?? null,
  }
}

/**
 * Parse result_summary_json which may be a string or object
 */
export function parseResults(data: JobResultSummary | string | null | undefined): JobResultSummary | null {
  if (!data) return null
  if (typeof data === 'object') return data
  if (typeof data === 'string') {
    try {
      return JSON.parse(data) as JobResultSummary
    } catch {
      return null
    }
  }
  return null
}

/**
 * Calculate host counts from job results
 */
export function calculateHostCounts(
  hostResults: Record<string, JobHostResult> | undefined
): { success: number; failed: number; partial: number; queued: number; running: number; total: number } | null {
  if (!hostResults) return null

  const counts = { success: 0, failed: 0, partial: 0, queued: 0, running: 0, total: 0 }

  Object.values(hostResults).forEach((res) => {
    const status = res.status || ''
    if (status === 'success') counts.success += 1
    else if (status === 'failed') counts.failed += 1
    else if (status === 'partial') counts.partial += 1
    else if (status === 'queued') counts.queued += 1
    else if (status === 'running') counts.running += 1
    counts.total += 1
  })

  return counts
}

/**
 * Check if a job is within the retry window (12 hours)
 */
export function isWithinRetryWindow(startedAt: string | null): boolean {
  if (!startedAt) return true
  const jobAgeMs = Date.now() - new Date(startedAt).getTime()
  const twelveHoursMs = 12 * 60 * 60 * 1000
  return jobAgeMs <= twelveHoursMs
}

/**
 * Check if a job can be retried
 */
export function canRetryJob(job: NormalizedJob): boolean {
  const retryableStatuses = ['failed', 'partial', 'queued', 'scheduled']
  return isWithinRetryWindow(job.started_at) && retryableStatuses.includes(job.status)
}

/**
 * Format job type for display
 */
export function formatJobType(type: string): string {
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
}

/**
 * Escape a value for CSV (handle quotes, commas, newlines)
 */
function escapeCSV(value: string): string {
  if (value.includes('"') || value.includes(',') || value.includes('\n') || value.includes('\r')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/**
 * Export job results to CSV format
 */
export function exportJobResultsToCSV(
  jobId: number,
  hostResults: Record<string, JobHostResult>
): void {
  const rows: string[] = []

  // Header row
  rows.push(['Hostname', 'Status', 'Command', 'Output', 'Error'].map(escapeCSV).join(','))

  // Data rows
  Object.entries(hostResults).forEach(([hostname, res]) => {
    if (res.results && typeof res.results === 'object') {
      // Multiple command results
      Object.entries(res.results).forEach(([cmd, output]) => {
        const outputStr = typeof output === 'string' ? output : JSON.stringify(output)
        rows.push(
          [hostname, res.status || '', cmd, outputStr, res.error || ''].map(escapeCSV).join(',')
        )
      })
    } else if (res.diff) {
      // Config diff result
      rows.push(
        [hostname, res.status || '', 'config_diff', res.diff, res.error || ''].map(escapeCSV).join(',')
      )
    } else if (res.result) {
      // Single result
      const resultStr = typeof res.result === 'string' ? res.result : JSON.stringify(res.result)
      rows.push(
        [hostname, res.status || '', '', resultStr, res.error || ''].map(escapeCSV).join(',')
      )
    } else if (res.error) {
      // Error only
      rows.push([hostname, res.status || '', '', '', res.error].map(escapeCSV).join(','))
    }
  })

  const csvContent = rows.join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)

  const link = document.createElement('a')
  link.href = url
  link.download = `job-${jobId}-results.csv`
  link.click()

  URL.revokeObjectURL(url)
}
