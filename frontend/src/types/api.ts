/**
 * Custom error class for API errors with response data
 */
export class ApiError extends Error {
  public readonly status: number
  public readonly data: Record<string, unknown>

  constructor(message: string, status: number, data: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.data = data
  }
}

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
