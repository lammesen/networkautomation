/**
 * MSW request handlers for API mocking in tests
 */
import { http, HttpResponse } from 'msw'
import type { User } from '@/types/user'
import type { Customer } from '@/types/customer'
import type { Device } from '@/types/device'
import type { Job } from '@/types/job'
import type { Credential } from '@/types/credential'

const API_BASE = 'http://localhost:8000/api/v1'

// Default mock data
const mockUser: User = {
  id: 1,
  username: 'testuser',
  email: 'test@example.com',
  is_active: true,
  is_admin: false,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
  customers: [],
}

const mockCustomers: Customer[] = [
  {
    id: 1,
    name: 'Test Customer',
    description: 'Test customer description',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

const mockDevices: Device[] = [
  {
    id: 1,
    hostname: 'router1',
    ip_address: '192.168.1.1',
    platform: 'cisco_ios',
    vendor: 'cisco',
    model: 'ISR4451',
    is_enabled: true,
    customer_id: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
]

const mockJobs: Job[] = [
  {
    id: 1,
    job_type: 'run_commands',
    status: 'success',
    payload: { commands: ['show version'] },
    result: null,
    error_message: null,
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    scheduled_for: null,
    user_id: 1,
    customer_id: 1,
  },
]

const mockCredentials: Credential[] = [
  {
    id: 1,
    name: 'default-creds',
    username: 'admin',
    customer_id: 1,
    created_at: new Date().toISOString(),
  },
]

/**
 * Default handlers for common API endpoints
 */
export const handlers = [
  // Auth
  http.post(`${API_BASE}/auth/login`, () => {
    return HttpResponse.json({
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
    })
  }),

  http.get(`${API_BASE}/auth/me`, () => {
    return HttpResponse.json(mockUser)
  }),

  http.post(`${API_BASE}/auth/register`, async ({ request }) => {
    const body = (await request.json()) as { username: string; password: string }
    return HttpResponse.json({
      ...mockUser,
      username: body.username,
    })
  }),

  // Customers
  http.get(`${API_BASE}/customers`, () => {
    return HttpResponse.json(mockCustomers)
  }),

  http.get(`${API_BASE}/customers/:id`, ({ params }) => {
    const customer = mockCustomers.find((c) => c.id === Number(params.id))
    if (!customer) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(customer)
  }),

  http.post(`${API_BASE}/customers`, async ({ request }) => {
    const body = (await request.json()) as { name: string; description?: string }
    return HttpResponse.json({
      id: mockCustomers.length + 1,
      name: body.name,
      description: body.description || null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  }),

  // Devices
  http.get(`${API_BASE}/devices`, () => {
    return HttpResponse.json({
      items: mockDevices,
      total: mockDevices.length,
    })
  }),

  http.get(`${API_BASE}/devices/:id`, ({ params }) => {
    const device = mockDevices.find((d) => d.id === Number(params.id))
    if (!device) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(device)
  }),

  http.post(`${API_BASE}/devices`, async ({ request }) => {
    const body = (await request.json()) as Partial<Device>
    return HttpResponse.json({
      id: mockDevices.length + 1,
      ...body,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
  }),

  http.put(`${API_BASE}/devices/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Partial<Device>
    const device = mockDevices.find((d) => d.id === Number(params.id))
    if (!device) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json({
      ...device,
      ...body,
      updated_at: new Date().toISOString(),
    })
  }),

  http.delete(`${API_BASE}/devices/:id`, () => {
    return new HttpResponse(null, { status: 204 })
  }),

  // Jobs
  http.get(`${API_BASE}/jobs`, () => {
    return HttpResponse.json(mockJobs)
  }),

  http.get(`${API_BASE}/jobs/:id`, ({ params }) => {
    const job = mockJobs.find((j) => j.id === Number(params.id))
    if (!job) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(job)
  }),

  http.get(`${API_BASE}/jobs/:id/logs`, () => {
    return HttpResponse.json([])
  }),

  http.post(`${API_BASE}/jobs/:id/retry`, ({ params }) => {
    return HttpResponse.json({
      job_id: Number(params.id) + 100,
      message: 'Job retry started',
    })
  }),

  // Admin jobs
  http.get(`${API_BASE}/jobs/admin`, () => {
    return HttpResponse.json(mockJobs)
  }),

  // Credentials
  http.get(`${API_BASE}/credentials`, () => {
    return HttpResponse.json(mockCredentials)
  }),

  http.post(`${API_BASE}/credentials`, async ({ request }) => {
    const body = (await request.json()) as { name: string; username: string; password: string }
    return HttpResponse.json({
      id: mockCredentials.length + 1,
      name: body.name,
      username: body.username,
      customer_id: 1,
      created_at: new Date().toISOString(),
    })
  }),

  // Commands
  http.post(`${API_BASE}/commands/run`, () => {
    return HttpResponse.json({
      job_id: 100,
      message: 'Job created',
    })
  }),

  http.get(`${API_BASE}/commands/suggestions`, () => {
    return HttpResponse.json(['show version', 'show ip route', 'show interfaces'])
  }),

  // Users
  http.get(`${API_BASE}/users`, () => {
    return HttpResponse.json([mockUser])
  }),

  http.put(`${API_BASE}/users/:id`, async ({ params, request }) => {
    const body = (await request.json()) as Partial<User>
    return HttpResponse.json({
      ...mockUser,
      id: Number(params.id),
      ...body,
      updated_at: new Date().toISOString(),
    })
  }),

  // Compliance
  http.get(`${API_BASE}/compliance/policies`, () => {
    return HttpResponse.json([])
  }),

  http.get(`${API_BASE}/compliance/results`, () => {
    return HttpResponse.json([])
  }),

  // Config
  http.get(`${API_BASE}/config/devices/:deviceId/snapshots`, () => {
    return HttpResponse.json([])
  }),
]

/**
 * Error handlers for testing error scenarios
 */
export const errorHandlers = {
  unauthorized: http.get(`${API_BASE}/auth/me`, () => {
    return HttpResponse.json({ detail: 'Not authenticated' }, { status: 401 })
  }),

  serverError: http.get(`${API_BASE}/devices`, () => {
    return HttpResponse.json({ detail: 'Internal server error' }, { status: 500 })
  }),

  notFound: http.get(`${API_BASE}/devices/:id`, () => {
    return HttpResponse.json({ detail: 'Device not found' }, { status: 404 })
  }),

  validationError: http.post(`${API_BASE}/devices`, () => {
    return HttpResponse.json(
      {
        detail: [
          {
            loc: ['body', 'hostname'],
            msg: 'field required',
            type: 'value_error.missing',
          },
        ],
      },
      { status: 422 }
    )
  }),
}
