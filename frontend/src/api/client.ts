import { useAuthStore } from '../store/authStore'
import type {
  ApiError as ApiErrorType,
  CompliancePolicy,
  CompliancePolicyCreate,
  ComplianceResult,
  ConfigDiff,
  ConfigSnapshot,
  Credential,
  CredentialCreate,
  Customer,
  CustomerCreate,
  Device,
  DeviceCreate,
  DeviceImportSummary,
  DeviceListResponse,
  DeviceUpdate,
  IPRange,
  IPRangeCreate,
  Job,
  JobCreateResponse,
  JobLog,
  JobRetryResponse,
  TokenResponse,
  User,
  UserUpdate,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

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

class ApiClient {
  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const { token, activeCustomerId } = useAuthStore.getState()

    const headers = new Headers(options.headers)
    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }

    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
    if (activeCustomerId) {
      headers.set('X-Customer-ID', activeCustomerId.toString())
    }

    const config: RequestInit = {
      ...options,
      headers,
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, config)

    if (response.status === 401) {
      useAuthStore.getState().clearAuth()
      window.location.href = '/login'
      throw new ApiError('Unauthorized', 401)
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      throw new ApiError(
        (errorData as { detail?: string }).detail || 'API Error',
        response.status,
        errorData as Record<string, unknown>
      )
    }

    // Handle empty/204 responses gracefully
    if (response.status === 204) {
      return null as T
    }
    const text = await response.text()
    if (!text) {
      return null as T
    }
    return JSON.parse(text) as T
  }

  // Auth
  login(username: string, password: string): Promise<TokenResponse> {
    return this.request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  }

  getMe(token?: string): Promise<User> {
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    return this.request<User>('/auth/me', { headers })
  }

  register(username: string, password: string): Promise<User> {
    return this.request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  }

  // Customers
  getCustomers(): Promise<Customer[]> {
    return this.request<Customer[]>('/customers')
  }

  createCustomer(data: CustomerCreate): Promise<Customer> {
    return this.request<Customer>('/customers', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  getCustomer(id: number): Promise<Customer> {
    return this.request<Customer>(`/customers/${id}`)
  }

  addUserToCustomer(customerId: number, userId: number): Promise<void> {
    return this.request<void>(`/customers/${customerId}/users/${userId}`, { method: 'POST' })
  }

  removeUserFromCustomer(customerId: number, userId: number): Promise<void> {
    return this.request<void>(`/customers/${customerId}/users/${userId}`, { method: 'DELETE' })
  }

  getCustomerIPRanges(customerId: number): Promise<IPRange[]> {
    return this.request<IPRange[]>(`/customers/${customerId}/ranges`)
  }

  createCustomerIPRange(customerId: number, data: IPRangeCreate): Promise<IPRange> {
    return this.request<IPRange>(`/customers/${customerId}/ranges`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  deleteCustomerIPRange(customerId: number, rangeId: number): Promise<void> {
    return this.request<void>(`/customers/${customerId}/ranges/${rangeId}`, { method: 'DELETE' })
  }

  // Users
  getUsers(params?: { active?: boolean }): Promise<User[]> {
    const queryString = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
    return this.request<User[]>(`/users${queryString}`)
  }

  updateUser(id: number, data: UserUpdate): Promise<User> {
    return this.request<User>(`/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  // Devices
  getDevices(params?: Record<string, string | number | boolean | undefined>): Promise<DeviceListResponse> {
    const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as Record<string, string>).toString()
    return this.request<DeviceListResponse>(`/devices?${queryString}`)
  }

  getDevice(id: number): Promise<Device> {
    return this.request<Device>(`/devices/${id}`)
  }

  createDevice(data: DeviceCreate): Promise<Device> {
    return this.request<Device>('/devices', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateDevice(id: number, data: DeviceUpdate): Promise<Device> {
    return this.request<Device>(`/devices/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteDevice(id: number): Promise<void> {
    return this.request<void>(`/devices/${id}`, { method: 'DELETE' })
  }

  importDevices(file: File): Promise<DeviceImportSummary> {
    const formData = new FormData()
    formData.append('file', file)
    return this.request<DeviceImportSummary>('/devices/import', {
      method: 'POST',
      body: formData,
    })
  }

  // Credentials
  getCredentials(): Promise<Credential[]> {
    return this.request<Credential[]>('/credentials')
  }

  createCredential(data: CredentialCreate): Promise<Credential> {
    return this.request<Credential>('/credentials', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Jobs
  getJobs(params?: Record<string, string | number | undefined>): Promise<Job[]> {
    const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as Record<string, string>).toString()
    return this.request<Job[]>(`/jobs?${queryString}`)
  }

  getJob(id: number): Promise<Job> {
    return this.request<Job>(`/jobs/${id}`)
  }

  getJobLogs(id: number): Promise<JobLog[]> {
    return this.request<JobLog[]>(`/jobs/${id}/logs`)
  }

  retryJob(id: number): Promise<JobRetryResponse> {
    return this.request<JobRetryResponse>(`/jobs/${id}/retry`, { method: 'POST' })
  }

  // Admin job visibility
  getAdminJobs(params?: Record<string, string | number | undefined>): Promise<Job[]> {
    const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as Record<string, string>).toString()
    return this.request<Job[]>(`/jobs/admin?${queryString}`)
  }

  getAdminJobLogs(id: number, limit = 1000): Promise<JobLog[]> {
    return this.request<JobLog[]>(`/jobs/admin/${id}/logs?limit=${limit}`)
  }

  // Commands
  runCommands(data: {
    targets: Record<string, unknown>
    commands: string[]
    timeout_sec?: number
    execute_at?: string
  }): Promise<JobCreateResponse> {
    return this.request<JobCreateResponse>('/commands/run', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  getCommandSuggestions(platform: string): Promise<string[]> {
    return this.request<string[]>(`/commands/suggestions?platform=${platform}`)
  }

  // Config snapshots & diffs
  getDeviceSnapshots(deviceId: number, limit = 50): Promise<ConfigSnapshot[]> {
    return this.request<ConfigSnapshot[]>(`/config/devices/${deviceId}/snapshots?limit=${limit}`)
  }

  getDeviceConfigDiff(deviceId: number, fromSnapshot: number, toSnapshot: number): Promise<ConfigDiff> {
    const params = new URLSearchParams({
      from: fromSnapshot.toString(),
      to: toSnapshot.toString(),
    }).toString()
    return this.request<ConfigDiff>(`/config/devices/${deviceId}/diff?${params}`)
  }

  // Compliance
  getCompliancePolicies(): Promise<CompliancePolicy[]> {
    return this.request<CompliancePolicy[]>('/compliance/policies')
  }

  getCompliancePolicy(id: number): Promise<CompliancePolicy> {
    return this.request<CompliancePolicy>(`/compliance/policies/${id}`)
  }

  createCompliancePolicy(data: CompliancePolicyCreate): Promise<CompliancePolicy> {
    return this.request<CompliancePolicy>('/compliance/policies', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  runComplianceCheck(policyId: number): Promise<JobCreateResponse> {
    return this.request<JobCreateResponse>('/compliance/run', {
      method: 'POST',
      body: JSON.stringify({ policy_id: policyId }),
    })
  }

  getComplianceResults(params?: {
    policy_id?: number
    device_id?: number
    status?: string
  }): Promise<ComplianceResult[]> {
    const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as Record<string, string>).toString()
    return this.request<ComplianceResult[]>(`/compliance/results?${queryString}`)
  }
}

export const apiClient = new ApiClient()
