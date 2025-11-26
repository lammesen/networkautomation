import * as React from 'react'
import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'

interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  ...props
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center py-12 px-4 text-center',
        className
      )}
      {...props}
    >
      {Icon && (
        <div className="rounded-full bg-muted p-3 mb-4">
          <Icon className="h-6 w-6 text-muted-foreground" />
        </div>
      )}
      <h3 className="text-lg font-medium text-foreground">{title}</h3>
      {description && (
        <p className="mt-1 text-sm text-muted-foreground max-w-sm">{description}</p>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

// Convenience wrapper for table empty states
interface TableEmptyStateProps {
  colSpan: number
  icon?: LucideIcon
  title?: string
  description?: string
  action?: React.ReactNode
}

export function TableEmptyState({
  colSpan,
  icon,
  title = 'No results found',
  description,
  action,
}: TableEmptyStateProps) {
  return (
    <tr>
      <td colSpan={colSpan}>
        <EmptyState
          icon={icon}
          title={title}
          description={description}
          action={action}
          className="py-16"
        />
      </td>
    </tr>
  )
}
