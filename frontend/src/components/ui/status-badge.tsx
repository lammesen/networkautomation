import { Badge } from './badge'
import { cn } from '@/lib/utils'

export type StatusType =
  | 'success'
  | 'running'
  | 'scheduled'
  | 'failed'
  | 'partial'
  | 'queued'
  | 'cancelled'
  | 'pass'
  | 'fail'
  | 'error'
  | 'active'
  | 'inactive'
  | 'enabled'
  | 'disabled'
  | 'reachable'
  | 'unreachable'
  | 'unknown'

const statusStyles: Record<string, string> = {
  // Job statuses
  success: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200',
  running: 'bg-blue-100 text-blue-800 hover:bg-blue-100 border-blue-200',
  scheduled: 'bg-indigo-100 text-indigo-800 hover:bg-indigo-100 border-indigo-200',
  failed: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',
  partial: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100 border-yellow-200',
  queued: 'bg-gray-100 text-gray-800 hover:bg-gray-100 border-gray-200',
  cancelled: 'bg-orange-100 text-orange-800 hover:bg-orange-100 border-orange-200',

  // Compliance statuses
  pass: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200',
  fail: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',
  error: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',

  // User/device statuses
  active: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200',
  inactive: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',
  enabled: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200',
  disabled: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',

  // Reachability
  reachable: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200',
  unreachable: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',
  unknown: 'bg-gray-100 text-gray-800 hover:bg-gray-100 border-gray-200',
}

interface StatusBadgeProps {
  status: string
  label?: string
  className?: string
}

/**
 * A reusable status badge component with consistent styling
 * across different status types (job, compliance, user, device).
 */
export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const normalizedStatus = status.toLowerCase()
  const styles = statusStyles[normalizedStatus] || statusStyles.unknown
  const displayLabel = label ?? status

  return (
    <Badge variant="outline" className={cn(styles, className)}>
      {displayLabel}
    </Badge>
  )
}

/**
 * Convenience component for boolean active/inactive status
 */
export function ActiveStatusBadge({
  isActive,
  className,
}: {
  isActive: boolean
  className?: string
}) {
  return (
    <StatusBadge
      status={isActive ? 'active' : 'inactive'}
      label={isActive ? 'Active' : 'Inactive'}
      className={className}
    />
  )
}

/**
 * Convenience component for boolean enabled/disabled status
 */
export function EnabledStatusBadge({
  isEnabled,
  className,
}: {
  isEnabled: boolean
  className?: string
}) {
  return (
    <StatusBadge
      status={isEnabled ? 'enabled' : 'disabled'}
      label={isEnabled ? 'Enabled' : 'Disabled'}
      className={className}
    />
  )
}
