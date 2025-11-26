export interface CompliancePolicy {
  id: number
  name: string
  description?: string | null
  scope_json: Record<string, unknown>
  definition_yaml?: string
  created_by: number
  created_at: string
  updated_at?: string
}

export interface CompliancePolicyCreate {
  name: string
  definition_yaml: string
  scope_json: Record<string, unknown>
  description?: string
}

export interface ComplianceResult {
  id: number
  policy_id: number
  device_id: number
  job_id: number
  ts: string
  status: 'pass' | 'fail' | 'error'
  details_json: Record<string, unknown>
}

export interface DeviceComplianceSummary {
  device_id: number
  policies: Array<{
    policy_id: number
    policy_name: string
    status: string
    last_check: string
    details: Record<string, unknown>
  }>
}
