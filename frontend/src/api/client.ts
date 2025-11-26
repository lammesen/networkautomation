import { useAuthStore } from '../store/authStore'
import { ApiError } from '@/lib/api/errors'
import type {
  AdminUserCreate,
  CompliancePolicy,
  CompliancePolicyCreate,
  ComplianceResult,
  ComplianceOverview,
  ConfigDiff,
  ConfigSnapshot,
  Credential,
  CredentialCreate,
  CredentialUpdate,
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

// Re-export ApiError for backward compatibility
export { ApiError } from '@/lib/api/errors'

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
    const queryString = params
      ? '?' + new URLSearchParams(params as Record<string, string>).toString()
      : ''
    return this.request<User[]>(`/users${queryString}`)
  }

  createUser(data: AdminUserCreate): Promise<User> {
    return this.request<User>('/users', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateUser(id: number, data: UserUpdate): Promise<User> {
    return this.request<User>(`/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  // Devices
  getDevices(
    params?: Record<string, string | number | boolean | undefined>
  ): Promise<DeviceListResponse> {
    const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as Record<string, string>).toString()
    return this.request<DeviceListResponse>(`/devices?${queryString}`)
  }

  getDevice(id: number): Promise<Device> {
    return this.request<Device>(`/devices/${id}`)
  }

  getDeviceJobs(
    deviceId: number,
    params?: { type?: string; status?: string; skip?: number; limit?: number }
  ): Promise<Job[]> {
    const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as Record<string, string>).toString()
    return this.request<Job[]>(`/devices/${deviceId}/jobs?${queryString}`)
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

  getCredential(id: number): Promise<Credential> {
    return this.request<Credential>(`/credentials/${id}`)
  }

  createCredential(data: CredentialCreate): Promise<Credential> {
    return this.request<Credential>('/credentials', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateCredential(id: number, data: CredentialUpdate): Promise<Credential> {
    return this.request<Credential>(`/credentials/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteCredential(id: number): Promise<void> {
    return this.request<void>(`/credentials/${id}`, { method: 'DELETE' })
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

  cancelJob(id: number): Promise<{ status: string }> {
    return this.request<{ status: string }>(`/jobs/${id}/cancel`, { method: 'POST' })
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

  getDeviceConfigDiff(
    deviceId: number,
    fromSnapshot: number,
    toSnapshot: number
  ): Promise<ConfigDiff> {
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
    start?: string
    end?: string
    skip?: number
    limit?: number
  }): Promise<ComplianceResult[]> {
    const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as Record<string, string>).toString()
    return this.request<ComplianceResult[]>(`/compliance/results?${queryString}`)
  }

  getComplianceOverview(recentLimit = 20): Promise<ComplianceOverview> {
    return this.request<ComplianceOverview>(`/compliance/overview?recent_limit=${recentLimit}`)
  }

  getComplianceResult(resultId: number): Promise<ComplianceResult> {
    return this.request<ComplianceResult>(`/compliance/results/${resultId}`)
  }

  // Config rollback
  rollbackPreview(snapshotId: number): Promise<JobCreateResponse> {
    return this.request<JobCreateResponse>('/config/rollback/preview', {
      method: 'POST',
      body: JSON.stringify({ snapshot_id: snapshotId }),
    })
  }

  rollbackCommit(previousJobId: number): Promise<JobCreateResponse> {
    return this.request<JobCreateResponse>('/config/rollback/commit', {
      method: 'POST',
      body: JSON.stringify({ previous_job_id: previousJobId, confirm: true }),
    })
  }

  getSnapshot(snapshotId: number): Promise<{
    id: number
    device_id: number
    created_at: string
    source: string
    config_text: string
    hash: string
  }> {
    return this.request(`/config/snapshots/${snapshotId}`)
  }

  // Config backup
  backupConfig(targets: Record<string, unknown> = {}): Promise<JobCreateResponse> {
    return this.request<JobCreateResponse>('/config/backup', {
      method: 'POST',
      body: JSON.stringify({ targets, source_label: 'manual' }),
    })
  }

  // Topology
  discoverTopology(targets: Record<string, unknown> = {}): Promise<JobCreateResponse> {
    return this.request<JobCreateResponse>('/topology/discover', {
      method: 'POST',
      body: JSON.stringify(targets),
    })
  }

  getTopologyLinks(deviceId?: number): Promise<
    Array<{
      id: number
      local_device_id: number
      local_device_hostname: string
      local_interface: string
      remote_device_id: number | null
      remote_device_hostname: string
      remote_interface: string
      remote_ip: string | null
      remote_platform: string | null
      protocol: string
      discovered_at: string
      is_known_device: boolean
    }>
  > {
    const params = deviceId ? `?device_id=${deviceId}` : ''
    return this.request(`/topology/links${params}`)
  }

  getTopologyGraph(): Promise<{
    nodes: Array<{
      id: string
      label: string
      data: {
        hostname: string
        mgmt_ip: string
        vendor?: string
        platform?: string
        role?: string
        site?: string
        reachability?: string
        is_unknown?: boolean
      }
      type: string
    }>
    edges: Array<{
      id: string
      source: string
      target: string
      data: {
        local_interface: string
        remote_interface: string
        protocol: string
        discovered_at: string
      }
    }>
    stats: {
      known_devices: number
      unknown_devices: number
      total_links: number
    }
  }> {
    return this.request('/topology/graph')
  }

  clearTopologyLinks(): Promise<{ deleted: number }> {
    return this.request('/topology/links', { method: 'DELETE' })
  }
}

export const apiClient = new ApiClient()
