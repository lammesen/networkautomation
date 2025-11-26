export interface Device {
  id: number
  hostname: string
  mgmt_ip: string
  vendor: string
  platform: string
  role?: string | null
  site?: string | null
  credentials_ref: number
  reachability_status?: string | null
  last_reachability_check?: string | null
  tags?: Record<string, unknown> | null
  enabled: boolean
  created_at?: string
  updated_at?: string
}

export interface DeviceCreate {
  hostname: string
  mgmt_ip: string
  vendor: string
  platform: string
  role?: string
  site?: string
  credentials_ref: number
  tags?: Record<string, unknown>
}

export interface DeviceUpdate {
  hostname?: string
  mgmt_ip?: string
  vendor?: string
  platform?: string
  role?: string
  site?: string
  credentials_ref?: number
  tags?: Record<string, unknown>
  enabled?: boolean
}

export interface DeviceFormData {
  id?: number
  hostname: string
  mgmt_ip: string
  vendor: string
  platform: string
  role: string
  site: string
  credentials_ref: number
}

export interface DeviceListResponse {
  total: number
  devices: Device[]
}

export interface DeviceImportSummary {
  created: number
  skipped: number
  failed: number
  errors: string[]
}

export const deviceSearchFieldOptions = [
  { key: 'hostname', label: 'Hostname' },
  { key: 'mgmt_ip', label: 'IP address' },
  { key: 'vendor', label: 'Vendor' },
  { key: 'platform', label: 'Platform' },
  { key: 'role', label: 'Role' },
  { key: 'site', label: 'Site' },
  { key: 'reachability_status', label: 'Reachability' },
  { key: 'status', label: 'Status (enabled/disabled)' },
] as const

export type DeviceSearchField = (typeof deviceSearchFieldOptions)[number]['key']
