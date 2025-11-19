import axios, { AxiosInstance } from 'axios'
import { useAuthStore } from '../store/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.request.use((config) => {
      const token = useAuthStore.getState().token
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    })

    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          useAuthStore.getState().clearAuth()
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  // Auth
  async login(username: string, password: string) {
    const response = await this.client.post('/auth/login', { username, password })
    return response.data
  }

  async getMe() {
    const response = await this.client.get('/auth/me')
    return response.data
  }

  // Devices
  async getDevices(params?: any) {
    const response = await this.client.get('/devices', { params })
    return response.data
  }

  async getDevice(id: number) {
    const response = await this.client.get(`/devices/${id}`)
    return response.data
  }

  async createDevice(data: any) {
    const response = await this.client.post('/devices', data)
    return response.data
  }

  async updateDevice(id: number, data: any) {
    const response = await this.client.put(`/devices/${id}`, data)
    return response.data
  }

  async deleteDevice(id: number) {
    await this.client.delete(`/devices/${id}`)
  }

  // Credentials
  async getCredentials() {
    const response = await this.client.get('/credentials')
    return response.data
  }

  async createCredential(data: any) {
    const response = await this.client.post('/credentials', data)
    return response.data
  }

  // Jobs
  async getJobs(params?: any) {
    const response = await this.client.get('/jobs', { params })
    return response.data
  }

  async getJob(id: number) {
    const response = await this.client.get(`/jobs/${id}`)
    return response.data
  }

  async getJobLogs(id: number) {
    const response = await this.client.get(`/jobs/${id}/logs`)
    return response.data
  }

  // Commands
  async runCommands(data: any) {
    const response = await this.client.post('/commands/run', data)
    return response.data
  }
}

export const apiClient = new ApiClient()
