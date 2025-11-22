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
  enabled: boolean
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

