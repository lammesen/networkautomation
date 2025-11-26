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

  /**
   * Check if error is an authentication error
   */
  isUnauthorized(): boolean {
    return this.status === 401
  }

  /**
   * Check if error is a forbidden error
   */
  isForbidden(): boolean {
    return this.status === 403
  }

  /**
   * Check if error is a not found error
   */
  isNotFound(): boolean {
    return this.status === 404
  }

  /**
   * Check if error is a validation error
   */
  isValidationError(): boolean {
    return this.status === 422
  }

  /**
   * Check if error is a server error
   */
  isServerError(): boolean {
    return this.status >= 500
  }

  /**
   * Get the detail message from the error data
   */
  getDetail(): string {
    return (this.data.detail as string) || this.message
  }
}

/**
 * Type guard to check if an error is an ApiError
 */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}
