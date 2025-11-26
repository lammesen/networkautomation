// Re-export ApiError from lib/api/errors for backward compatibility
export { ApiError, isApiError } from '@/lib/api/errors'

/**
 * Generic paginated response type
 */
export interface PaginatedResponse<T> {
  total: number
  items: T[]
  skip?: number
  limit?: number
}

/**
 * Auth response types
 */
export interface TokenResponse {
  access_token: string
  refresh_token: string
}

/**
 * Config snapshot types
 */
export interface ConfigSnapshot {
  id: number
  device_id: number
  created_at: string
  source: string
  config_text?: string
  hash: string
  job_id?: number | null
}

export interface ConfigDiff {
  device_id: number
  from_snapshot: number
  to_snapshot: number
  diff: string
}
