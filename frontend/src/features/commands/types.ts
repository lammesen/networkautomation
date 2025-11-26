export interface CommandTargets {
  site: string
  role: string
  vendor: string
  platform: string
}

export interface RunCommandsPayload {
  targets: Record<string, string>
  commands: string[]
  timeout_sec?: number
  execute_at?: string
}

export const SUPPORTED_PLATFORMS = ['ios', 'nxos', 'eos', 'junos'] as const
export type SupportedPlatform = typeof SUPPORTED_PLATFORMS[number]

export const DEFAULT_COMMAND_SNIPPETS = [
  'show version',
  'show ip interface brief',
  'show interfaces description',
  'show inventory',
  'show logging last 50',
  'show configuration | display set',
] as const
