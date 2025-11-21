import { useAuthStore } from '../store/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
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
      throw new Error('Unauthorized')
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}))
      const error = new Error(errorData.detail || 'API Error')
      // @ts-ignore
      error.response = { data: errorData, status: response.status }
      throw error
    }

    return response.json()
  }

  // Auth
  login(username: string, password: string) {
    return this.request<{ access_token: string; refresh_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  }

  getMe(token?: string) {
    const headers: Record<string, string> = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    return this.request<any>('/auth/me', { headers })
  }

  register(username: string, password: string) {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
  }

  // Customers
  getCustomers() {
    return this.request<any[]>('/customers')
  }

  createCustomer(data: { name: string; description?: string }) {
    return this.request('/customers', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  getCustomer(id: number) {
    return this.request(`/customers/${id}`)
  }

  addUserToCustomer(customerId: number, userId: number) {
    return this.request(`/customers/${customerId}/users/${userId}`, { method: 'POST' })
  }

  removeUserFromCustomer(customerId: number, userId: number) {
    return this.request(`/customers/${customerId}/users/${userId}`, { method: 'DELETE' })
  }

  getCustomerIPRanges(customerId: number) {
    return this.request<any[]>(`/customers/${customerId}/ranges`)
  }

  createCustomerIPRange(customerId: number, data: { cidr: string; description?: string }) {
    return this.request(`/customers/${customerId}/ranges`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  deleteCustomerIPRange(customerId: number, rangeId: number) {
    return this.request(`/customers/${customerId}/ranges/${rangeId}`, { method: 'DELETE' })
  }

  // Users
  getUsers(params?: { active?: boolean }) {
    const queryString = params ? '?' + new URLSearchParams(params as any).toString() : ''
    return this.request<any[]>(`/users${queryString}`)
  }

  updateUser(id: number, data: { role?: string; is_active?: boolean }) {
    return this.request(`/users/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  // Devices
  getDevices(params?: any) {
    // Clean undefined params
    const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as any).toString()
    return this.request<{ total: number; devices: any[] }>(`/devices?${queryString}`)
  }

  getDevice(id: number) {
    return this.request(`/devices/${id}`)
  }

  createDevice(data: any) {
    return this.request('/devices', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  updateDevice(id: number, data: any) {
    return this.request(`/devices/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  deleteDevice(id: number) {
    return this.request(`/devices/${id}`, { method: 'DELETE' })
  }

  importDevices(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return this.request('/devices/import', {
      method: 'POST',
      body: formData,
    })
  }

  // Credentials
  getCredentials() {
    return this.request<any[]>('/credentials')
  }

  createCredential(data: any) {
    return this.request('/credentials', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  // Jobs
  getJobs(params?: any) {
     const cleanParams = Object.fromEntries(
      Object.entries(params || {}).filter(([_, v]) => v != null && v !== '')
    )
    const queryString = new URLSearchParams(cleanParams as any).toString()
    return this.request<any[]>(`/jobs?${queryString}`)
  }

  getJob(id: number) {
    return this.request(`/jobs/${id}`)
  }

  getJobLogs(id: number) {
    return this.request(`/jobs/${id}/logs`)
  }

  // Commands
  runCommands(data: any) {
    return this.request('/commands/run', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  getCommandSuggestions(platform: string) {
    return this.request<string[]>(`/commands/suggestions?platform=${platform}`)
  }
}

export const apiClient = new ApiClient()