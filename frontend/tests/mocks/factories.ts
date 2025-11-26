/**
 * Mock data factories for testing
 */

import type { User } from '@/types/user'
import type { Customer } from '@/types/customer'
import type { Device, DeviceFilters } from '@/types/device'
import type { Job, JobStatus, JobType } from '@/types/job'
import type { Credential } from '@/types/credential'

let idCounter = 1

function nextId(): number {
  return idCounter++
}

/**
 * Reset the ID counter between tests
 */
export function resetMockIds(): void {
  idCounter = 1
}

/**
 * Create a mock User
 */
export function createMockUser(overrides: Partial<User> = {}): User {
  const id = nextId()
  return {
    id,
    username: `user${id}`,
    email: `user${id}@example.com`,
    is_active: true,
    is_admin: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    customers: [],
    ...overrides,
  }
}

/**
 * Create a mock Customer
 */
export function createMockCustomer(overrides: Partial<Customer> = {}): Customer {
  const id = nextId()
  return {
    id,
    name: `Customer ${id}`,
    description: `Description for customer ${id}`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }
}

/**
 * Create a mock Device
 */
export function createMockDevice(overrides: Partial<Device> = {}): Device {
  const id = nextId()
  return {
    id,
    hostname: `device${id}`,
    ip_address: `192.168.1.${id}`,
    platform: 'linux',
    vendor: 'generic',
    model: 'generic',
    is_enabled: true,
    customer_id: 1,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    ...overrides,
  }
}

/**
 * Create a mock Credential
 */
export function createMockCredential(overrides: Partial<Credential> = {}): Credential {
  const id = nextId()
  return {
    id,
    name: `credential${id}`,
    username: `admin${id}`,
    customer_id: 1,
    created_at: new Date().toISOString(),
    ...overrides,
  }
}

/**
 * Create a mock Job
 */
export function createMockJob(overrides: Partial<Job> = {}): Job {
  const id = nextId()
  return {
    id,
    job_type: 'run_commands' as JobType,
    status: 'success' as JobStatus,
    payload: { commands: ['show version'] },
    result: null,
    error_message: null,
    created_at: new Date().toISOString(),
    started_at: new Date().toISOString(),
    finished_at: new Date().toISOString(),
    scheduled_for: null,
    user_id: 1,
    customer_id: 1,
    ...overrides,
  }
}

/**
 * Create mock device filters
 */
export function createMockDeviceFilters(overrides: Partial<DeviceFilters> = {}): DeviceFilters {
  return {
    hostname: '',
    ip_address: '',
    platform: '',
    vendor: '',
    is_enabled: undefined,
    page: 1,
    per_page: 50,
    ...overrides,
  }
}

/**
 * Create an array of mock items
 */
export function createMockArray<T>(
  factory: (overrides?: Partial<T>) => T,
  count: number,
  overrides?: Partial<T>
): T[] {
  return Array.from({ length: count }, () => factory(overrides))
}
