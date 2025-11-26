import * as React from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { EmptyState } from '@/components/ui/empty-state'
import { cn } from '@/lib/utils'
import { ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, LucideIcon } from 'lucide-react'

// Column definition
export interface DataTableColumn<T> {
  id: string
  header: string | React.ReactNode
  accessorKey?: keyof T
  accessorFn?: (row: T) => React.ReactNode
  cell?: (row: T) => React.ReactNode
  sortable?: boolean
  className?: string
  headerClassName?: string
}

// Sort state
export type SortDirection = 'asc' | 'desc' | null
export interface SortState {
  column: string | null
  direction: SortDirection
}

// Props
interface DataTableProps<T> {
  data: T[]
  columns: DataTableColumn<T>[]
  keyField: keyof T
  // Sorting
  sortable?: boolean
  defaultSort?: SortState
  onSortChange?: (sort: SortState) => void
  // Pagination
  pageSize?: number
  showPagination?: boolean
  // Empty state
  emptyIcon?: LucideIcon
  emptyTitle?: string
  emptyDescription?: string
  emptyAction?: React.ReactNode
  // Row styling
  rowClassName?: string | ((row: T) => string)
  onRowClick?: (row: T) => void
  // Table styling
  className?: string
}

export function DataTable<T>({
  data,
  columns,
  keyField,
  sortable = false,
  defaultSort = { column: null, direction: null },
  onSortChange,
  pageSize = 10,
  showPagination = false,
  emptyIcon,
  emptyTitle = 'No results found',
  emptyDescription,
  emptyAction,
  rowClassName,
  onRowClick,
  className,
}: DataTableProps<T>) {
  const [sort, setSort] = React.useState<SortState>(defaultSort)
  const [currentPage, setCurrentPage] = React.useState(0)

  // Handle sort toggle
  const handleSort = (columnId: string) => {
    const newSort: SortState = {
      column: columnId,
      direction:
        sort.column === columnId
          ? sort.direction === 'asc'
            ? 'desc'
            : sort.direction === 'desc'
              ? null
              : 'asc'
          : 'asc',
    }
    if (newSort.direction === null) {
      newSort.column = null
    }
    setSort(newSort)
    onSortChange?.(newSort)
  }

  // Sort data if needed (client-side sorting)
  const sortedData = React.useMemo(() => {
    if (!sort.column || !sort.direction) return data

    const column = columns.find((c) => c.id === sort.column)
    if (!column) return data

    return [...data].sort((a, b) => {
      let aVal: unknown
      let bVal: unknown

      if (column.accessorFn) {
        aVal = column.accessorFn(a)
        bVal = column.accessorFn(b)
      } else if (column.accessorKey) {
        aVal = a[column.accessorKey]
        bVal = b[column.accessorKey]
      } else {
        return 0
      }

      // Handle null/undefined
      if (aVal == null && bVal == null) return 0
      if (aVal == null) return sort.direction === 'asc' ? 1 : -1
      if (bVal == null) return sort.direction === 'asc' ? -1 : 1

      // Compare
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        return sort.direction === 'asc'
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal)
      }

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sort.direction === 'asc' ? aVal - bVal : bVal - aVal
      }

      // Fallback to string comparison
      const aStr = String(aVal)
      const bStr = String(bVal)
      return sort.direction === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr)
    })
  }, [data, sort, columns])

  // Paginate data
  const paginatedData = React.useMemo(() => {
    if (!showPagination) return sortedData
    const start = currentPage * pageSize
    return sortedData.slice(start, start + pageSize)
  }, [sortedData, currentPage, pageSize, showPagination])

  const totalPages = Math.ceil(sortedData.length / pageSize)

  // Reset to first page when data changes
  React.useEffect(() => {
    setCurrentPage(0)
  }, [data.length])

  // Get cell value
  const getCellValue = (row: T, column: DataTableColumn<T>) => {
    if (column.cell) return column.cell(row)
    if (column.accessorFn) return column.accessorFn(row)
    if (column.accessorKey) return row[column.accessorKey] as React.ReactNode
    return null
  }

  // Render sort indicator
  const renderSortIndicator = (columnId: string) => {
    if (sort.column !== columnId) {
      return <ArrowUpDown className="ml-2 h-4 w-4 text-muted-foreground/50" />
    }
    if (sort.direction === 'asc') {
      return <ArrowUp className="ml-2 h-4 w-4" />
    }
    return <ArrowDown className="ml-2 h-4 w-4" />
  }

  return (
    <div className={cn('w-full', className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((column) => (
              <TableHead
                key={column.id}
                className={cn(
                  column.headerClassName,
                  sortable && column.sortable !== false && 'cursor-pointer select-none'
                )}
                onClick={
                  sortable && column.sortable !== false
                    ? () => handleSort(column.id)
                    : undefined
                }
              >
                <div className="flex items-center">
                  {column.header}
                  {sortable && column.sortable !== false && renderSortIndicator(column.id)}
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {paginatedData.length > 0 ? (
            paginatedData.map((row) => {
              const key = String(row[keyField])
              const rowClass =
                typeof rowClassName === 'function' ? rowClassName(row) : rowClassName

              return (
                <TableRow
                  key={key}
                  className={cn(
                    rowClass,
                    onRowClick && 'cursor-pointer'
                  )}
                  onClick={onRowClick ? () => onRowClick(row) : undefined}
                >
                  {columns.map((column) => (
                    <TableCell key={column.id} className={column.className}>
                      {getCellValue(row, column)}
                    </TableCell>
                  ))}
                </TableRow>
              )
            })
          ) : (
            <TableRow>
              <TableCell colSpan={columns.length}>
                <EmptyState
                  icon={emptyIcon}
                  title={emptyTitle}
                  description={emptyDescription}
                  action={emptyAction}
                  className="py-12"
                />
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>

      {/* Pagination */}
      {showPagination && totalPages > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t">
          <p className="text-sm text-muted-foreground">
            Showing {currentPage * pageSize + 1} to{' '}
            {Math.min((currentPage + 1) * pageSize, sortedData.length)} of {sortedData.length}{' '}
            results
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
              disabled={currentPage === 0}
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </Button>
            <span className="text-sm text-muted-foreground">
              Page {currentPage + 1} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={currentPage >= totalPages - 1}
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
