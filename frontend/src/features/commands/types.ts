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

// Dangerous command patterns that require extra confirmation
// These commands can cause service disruption, data loss, or configuration changes
export const DANGEROUS_COMMAND_PATTERNS = [
  // Reload/reboot commands
  /^reload\b/i,
  /^reboot\b/i,
  /^request system reboot/i,
  /^system reboot/i,

  // Erase/delete commands
  /^write erase\b/i,
  /^erase startup-config/i,
  /^erase nvram/i,
  /^delete\s+/i,
  /^request system zeroize/i,

  // Format commands
  /^format\s+/i,

  // Configuration reset
  /^copy\s+.*\s+startup-config/i,
  /^configure replace/i,
  /^rollback\b/i,
  /^load override/i,
  /^load replace/i,

  // Interface shutdown (potential service impact)
  /^shutdown\b/i,
  /^no shutdown\b/i,

  // Routing protocol changes
  /^router\s+(bgp|ospf|isis|eigrp)\b/i,
  /^no router\s+(bgp|ospf|isis|eigrp)\b/i,

  // VRF changes
  /^(no\s+)?vrf\s+/i,

  // License commands
  /^license\s+/i,

  // Debug commands (can impact performance)
  /^debug\s+/i,

  // NX-OS specific
  /^install all/i,
  /^copy running-config startup-config/i,
  /^write memory/i,

  // Junos specific
  /^request system halt/i,
  /^request system power-off/i,
  /^commit\b/i,
] as const

/**
 * Check if a command matches any dangerous pattern
 */
export function isDangerousCommand(command: string): boolean {
  const trimmed = command.trim()
  return DANGEROUS_COMMAND_PATTERNS.some((pattern) => pattern.test(trimmed))
}

/**
 * Filter commands to find dangerous ones
 */
export function findDangerousCommands(commands: string[]): string[] {
  return commands.filter(isDangerousCommand)
}
