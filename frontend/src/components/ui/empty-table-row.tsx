import { TableCell, TableRow } from './table'
import { cn } from '@/lib/utils'

interface EmptyTableRowProps {
  colSpan: number
  message?: string
  className?: string
}

/**
 * A reusable empty state row for tables.
 * Use when there's no data to display in a table.
 */
export function EmptyTableRow({
  colSpan,
  message = 'No data found',
  className,
}: EmptyTableRowProps) {
  return (
    <TableRow>
      <TableCell
        colSpan={colSpan}
        className={cn('text-center h-24 text-muted-foreground', className)}
      >
        {message}
      </TableCell>
    </TableRow>
  )
}
