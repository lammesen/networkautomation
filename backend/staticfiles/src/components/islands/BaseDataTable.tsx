import * as React from "react";
import {
  ColumnDef,
  ColumnFiltersState,
  SortingState,
  VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  RowSelectionState,
} from "@tanstack/react-table";
import { ChevronDown, ChevronUp, ChevronsUpDown, MoreHorizontal } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";

// Types
export type RowAction<TData> = {
  label: string;
  onClick: (row: TData) => void;
  variant?: "default" | "destructive";
  disabled?: (row: TData) => boolean;
};

export type BulkAction<TData> = {
  label: string;
  icon?: React.ReactNode;
  onClick: (selectedRows: TData[]) => void;
  variant?: "default" | "destructive" | "outline";
};

export type BaseDataTableProps<TData, TValue> = {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchColumn?: string;
  searchPlaceholder?: string;
  rowActions?: RowAction<TData>[];
  bulkActions?: BulkAction<TData>[];
  emptyState?: {
    icon?: React.ReactNode;
    title: string;
    description?: string;
  };
  pageSize?: number;
  pageSizeOptions?: number[];
  enableSelection?: boolean;
  enablePagination?: boolean;
  enableSearch?: boolean;
  onRowClick?: (row: TData) => void;
  getRowId?: (row: TData) => string;
};

// Sort header component
function SortHeader({
  column,
  children,
}: {
  column: any;
  children: React.ReactNode;
}) {
  const sorted = column.getIsSorted();
  return (
    <button
      className="flex items-center gap-1 hover:text-foreground transition-colors -ml-2 px-2 py-1 rounded-md hover:bg-accent"
      onClick={() => column.toggleSorting(sorted === "asc")}
    >
      {children}
      {sorted === "asc" ? (
        <ChevronUp className="h-4 w-4" />
      ) : sorted === "desc" ? (
        <ChevronDown className="h-4 w-4" />
      ) : (
        <ChevronsUpDown className="h-4 w-4 opacity-50" />
      )}
    </button>
  );
}

// Selection column helper
export function createSelectColumn<TData>(): ColumnDef<TData> {
  return {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={
          table.getIsAllPageRowsSelected() ||
          (table.getIsSomePageRowsSelected() && "indeterminate")
        }
        onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
        aria-label="Select all"
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        onCheckedChange={(value) => row.toggleSelected(!!value)}
        aria-label="Select row"
      />
    ),
    enableSorting: false,
    enableHiding: false,
    size: 40,
  };
}

// Actions column helper
export function createActionsColumn<TData>(
  actions: RowAction<TData>[]
): ColumnDef<TData> {
  return {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <span className="sr-only">Open menu</span>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-40">
          {actions.map((action, idx) => (
            <DropdownMenuItem
              key={idx}
              onClick={() => action.onClick(row.original)}
              disabled={action.disabled?.(row.original)}
              className={action.variant === "destructive" ? "text-destructive focus:text-destructive" : ""}
            >
              {action.label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    ),
    enableSorting: false,
    enableHiding: false,
    size: 50,
  };
}

// Main component
export function BaseDataTable<TData, TValue>({
  columns,
  data,
  // searchColumn can be used for column-specific filtering in the future
  searchColumn: _searchColumn,
  searchPlaceholder = "Search...",
  rowActions,
  bulkActions,
  emptyState,
  pageSize = 10,
  pageSizeOptions = [10, 20, 50, 100],
  enableSelection = false,
  enablePagination = true,
  enableSearch = true,
  onRowClick,
  getRowId,
}: BaseDataTableProps<TData, TValue>) {
  const [sorting, setSorting] = React.useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({});
  const [globalFilter, setGlobalFilter] = React.useState("");

  // Build columns with selection and actions if needed
  const tableColumns = React.useMemo(() => {
    const cols = [...columns];
    
    if (enableSelection && !cols.find((c) => c.id === "select")) {
      cols.unshift(createSelectColumn<TData>());
    }
    
    if (rowActions?.length && !cols.find((c) => c.id === "actions")) {
      cols.push(createActionsColumn<TData>(rowActions));
    }
    
    return cols;
  }, [columns, enableSelection, rowActions]);

  const table = useReactTable({
    data,
    columns: tableColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: enablePagination ? getPaginationRowModel() : undefined,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: "includesString",
    getRowId: getRowId as any,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      rowSelection,
      globalFilter,
    },
    initialState: {
      pagination: {
        pageSize,
      },
    },
  });

  const selectedRows = table.getFilteredSelectedRowModel().rows.map((r) => r.original);

  // Empty state
  if (!data.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
        {emptyState?.icon && (
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
            {emptyState.icon}
          </div>
        )}
        <p className="text-base font-medium">{emptyState?.title || "No data"}</p>
        {emptyState?.description && (
          <p className="text-sm text-muted-foreground">{emptyState.description}</p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between gap-4">
        {/* Search */}
        {enableSearch && (
          <Input
            placeholder={searchPlaceholder}
            value={globalFilter ?? ""}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="max-w-sm"
          />
        )}

        {/* Bulk actions */}
        {bulkActions && selectedRows.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {selectedRows.length} selected
            </span>
            {bulkActions.map((action, idx) => (
              <Button
                key={idx}
                variant={action.variant || "outline"}
                size="sm"
                onClick={() => action.onClick(selectedRows)}
              >
                {action.icon}
                {action.label}
              </Button>
            ))}
          </div>
        )}
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    style={{ width: header.column.columnDef.size }}
                  >
                    {header.isPlaceholder
                      ? null
                      : header.column.getCanSort()
                      ? (
                        <SortHeader column={header.column}>
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </SortHeader>
                      )
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                  className={cn(onRowClick && "cursor-pointer")}
                  onClick={() => onRowClick?.(row.original)}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={tableColumns.length} className="h-24 text-center">
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {enablePagination && (
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>Rows per page</span>
            <Select
              value={`${table.getState().pagination.pageSize}`}
              onValueChange={(value) => table.setPageSize(Number(value))}
            >
              <SelectTrigger className="h-8 w-[70px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent side="top">
                {pageSizeOptions.map((size) => (
                  <SelectItem key={size} value={`${size}`}>
                    {size}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Page {table.getState().pagination.pageIndex + 1} of{" "}
              {table.getPageCount()}
            </span>
            <div className="flex items-center gap-1">
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
              >
                Next
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Export helper for creating sortable columns
export function createSortableColumn<TData, TValue>(
  accessorKey: keyof TData,
  header: string,
  options?: Partial<ColumnDef<TData, TValue>>
): ColumnDef<TData, TValue> {
  return {
    accessorKey: accessorKey as string,
    header: () => header,
    enableSorting: true,
    ...options,
  } as ColumnDef<TData, TValue>;
}

export default BaseDataTable;
