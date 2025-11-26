/**
 * API endpoint constants
 */
export const API_ENDPOINTS = {
  // Auth
  AUTH_LOGIN: '/auth/login',
  AUTH_REGISTER: '/auth/register',
  AUTH_ME: '/auth/me',

  // Customers
  CUSTOMERS: '/customers',
  CUSTOMER: (id: number) => `/customers/${id}`,
  CUSTOMER_USERS: (customerId: number, userId: number) => `/customers/${customerId}/users/${userId}`,
  CUSTOMER_RANGES: (customerId: number) => `/customers/${customerId}/ranges`,
  CUSTOMER_RANGE: (customerId: number, rangeId: number) => `/customers/${customerId}/ranges/${rangeId}`,

  // Users
  USERS: '/users',
  USER: (id: number) => `/users/${id}`,

  // Devices
  DEVICES: '/devices',
  DEVICE: (id: number) => `/devices/${id}`,
  DEVICES_IMPORT: '/devices/import',

  // Credentials
  CREDENTIALS: '/credentials',

  // Jobs
  JOBS: '/jobs',
  JOB: (id: number) => `/jobs/${id}`,
  JOB_LOGS: (id: number) => `/jobs/${id}/logs`,
  JOB_RETRY: (id: number) => `/jobs/${id}/retry`,
  JOBS_ADMIN: '/jobs/admin',
  ADMIN_JOB_LOGS: (id: number, limit: number) => `/jobs/admin/${id}/logs?limit=${limit}`,

  // Commands
  COMMANDS_RUN: '/commands/run',
  COMMAND_SUGGESTIONS: (platform: string) => `/commands/suggestions?platform=${platform}`,

  // Config
  DEVICE_SNAPSHOTS: (deviceId: number, limit: number) => `/config/devices/${deviceId}/snapshots?limit=${limit}`,
  DEVICE_CONFIG_DIFF: (deviceId: number, from: number, to: number) =>
    `/config/devices/${deviceId}/diff?from=${from}&to=${to}`,

  // Compliance
  COMPLIANCE_POLICIES: '/compliance/policies',
  COMPLIANCE_POLICY: (id: number) => `/compliance/policies/${id}`,
  COMPLIANCE_RUN: '/compliance/run',
  COMPLIANCE_RESULTS: '/compliance/results',
} as const
