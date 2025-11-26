/**
 * Shared date/time formatters for consistent display across the app
 */

const relativeFormatter = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

function pad(num: number): string {
  return num.toString().padStart(2, '0')
}

function formatParts(date: Date): { date: string; time: string } {
  const day = pad(date.getUTCDate())
  const month = pad(date.getUTCMonth() + 1)
  const year = date.getUTCFullYear()
  const hours = pad(date.getUTCHours())
  const minutes = pad(date.getUTCMinutes())
  const seconds = pad(date.getUTCSeconds())
  return {
    date: `${day}/${month}/${year}`,
    time: `${hours}:${minutes}:${seconds}`,
  }
}

/**
 * Format a date string to a localized date-time string
 */
export function formatDateTime(date: string | Date | null | undefined): string {
  if (!date) return '-'
  try {
    const d = typeof date === 'string' ? new Date(date) : date
    const parts = formatParts(d)
    return `${parts.date} ${parts.time}`
  } catch {
    return '-'
  }
}

/**
 * Format a date string to a localized date string (no time)
 */
export function formatDate(date: string | Date | null | undefined): string {
  if (!date) return '-'
  try {
    const d = typeof date === 'string' ? new Date(date) : date
    return formatParts(d).date
  } catch {
    return '-'
  }
}

/**
 * Format a date string to a localized time string (no date)
 */
export function formatTime(date: string | Date | null | undefined): string {
  if (!date) return '-'
  try {
    const d = typeof date === 'string' ? new Date(date) : date
    return formatParts(d).time
  } catch {
    return '-'
  }
}

/**
 * Format a date as relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: string | Date | null | undefined): string {
  if (!date) return '-'
  try {
    const d = typeof date === 'string' ? new Date(date) : date
    const now = new Date()
    const diffMs = d.getTime() - now.getTime()
    const diffSeconds = Math.round(diffMs / 1000)
    const diffMinutes = Math.round(diffSeconds / 60)
    const diffHours = Math.round(diffMinutes / 60)
    const diffDays = Math.round(diffHours / 24)

    if (Math.abs(diffSeconds) < 60) {
      return relativeFormatter.format(diffSeconds, 'second')
    } else if (Math.abs(diffMinutes) < 60) {
      return relativeFormatter.format(diffMinutes, 'minute')
    } else if (Math.abs(diffHours) < 24) {
      return relativeFormatter.format(diffHours, 'hour')
    } else {
      return relativeFormatter.format(diffDays, 'day')
    }
  } catch {
    return '-'
  }
}

/**
 * Format duration in milliseconds to human-readable string
 */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '-'

  const seconds = Math.floor(ms / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}h ${minutes % 60}m ${seconds % 60}s`
  } else if (minutes > 0) {
    return `${minutes}m ${seconds % 60}s`
  } else {
    return `${seconds}s`
  }
}

/**
 * Calculate duration between two dates in milliseconds
 */
export function calculateDuration(
  start: string | Date | null | undefined,
  end: string | Date | null | undefined
): number | null {
  if (!start || !end) return null
  try {
    const startDate = typeof start === 'string' ? new Date(start) : start
    const endDate = typeof end === 'string' ? new Date(end) : end
    return endDate.getTime() - startDate.getTime()
  } catch {
    return null
  }
}
