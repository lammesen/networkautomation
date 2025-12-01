import { useEffect, useMemo, useState, useCallback } from "react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import { cn } from "@/lib/utils";

type DeviceRow = {
  id: number;
  hostname: string;
  mgmtIp: string;
  vendor?: string;
  platform?: string;
  site?: string;
  enabled: boolean;
  detailUrl: string;
  apiUrl?: string;
};

type SortKey = "hostname" | "mgmtIp" | "vendor" | "platform" | "site" | "enabled";
type SortDirection = "asc" | "desc";

type DataTableProps = {
  rows: DeviceRow[];
  emptyState?: {
    title: string;
    description?: string;
  };
};

declare global {
  interface Window {
    toggleAllDevices?: (checked: boolean) => void;
    updateBulkActionBar?: () => void;
    clearSelection?: () => void;
    openRunTaskWizard?: () => void;
    webnet?: {
      getCsrfToken?: () => string;
      showToast?: (message: string, variant?: "success" | "error") => void;
    };
  }
}

const sorters: Record<SortKey, (a: DeviceRow, b: DeviceRow) => number> = {
  hostname: (a, b) => a.hostname.localeCompare(b.hostname),
  mgmtIp: (a, b) => a.mgmtIp.localeCompare(b.mgmtIp),
  vendor: (a, b) => (a.vendor || "").localeCompare(b.vendor || ""),
  platform: (a, b) => (a.platform || "").localeCompare(b.platform || ""),
  site: (a, b) => (a.site || "").localeCompare(b.site || ""),
  enabled: (a, b) => Number(a.enabled) - Number(b.enabled),
};

const SortIcon = ({ direction }: { direction: SortDirection | null }) => {
  if (!direction) {
    return (
      <svg
        xmlns="http://www.w3.org/2000/svg"
        className="h-4 w-4 text-muted-foreground/50"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
      </svg>
    );
  }
  return direction === "asc" ? (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
    </svg>
  ) : (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
    </svg>
  );
};

export function DataTable({ rows, emptyState }: DataTableProps) {
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const sortedRows = useMemo(() => {
    if (!sortKey) return rows;
    const sorted = [...rows].sort(sorters[sortKey]);
    return sortDirection === "desc" ? sorted.reverse() : sorted;
  }, [rows, sortKey, sortDirection]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDirection((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDirection("asc");
    }
  };

  const handleSelectAll = useCallback((checked: boolean) => {
    if (checked) {
      setSelectedIds(new Set(rows.map((r) => r.id)));
    } else {
      setSelectedIds(new Set());
    }
  }, [rows]);

  const handleSelectOne = useCallback((id: number, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(id);
      } else {
        next.delete(id);
      }
      return next;
    });
  }, []);

  // Sync with the parent page's bulk action bar
  useEffect(() => {
    // Call the parent page's updateBulkActionBar function after selection changes
    // We need to ensure the DOM checkboxes reflect our state first
    requestAnimationFrame(() => {
      if (typeof window.updateBulkActionBar === "function") {
        window.updateBulkActionBar();
      }
    });
  }, [selectedIds]);

  // Expose functions to window for the parent page's JS to call
  useEffect(() => {
    window.toggleAllDevices = handleSelectAll;
    window.clearSelection = () => setSelectedIds(new Set());
    return () => {
      delete window.toggleAllDevices;
      delete window.clearSelection;
    };
  }, [handleSelectAll]);

  const allSelected = rows.length > 0 && selectedIds.size === rows.length;
  const someSelected = selectedIds.size > 0 && selectedIds.size < rows.length;

  if (rows.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-12 w-12 text-muted-foreground"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1}
            d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
          />
        </svg>
        <p className="mt-4 font-medium text-foreground">
          {emptyState?.title || "No devices found"}
        </p>
        {emptyState?.description && (
          <p className="mt-1 text-sm text-muted-foreground">{emptyState.description}</p>
        )}
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-12">
            <input
              type="checkbox"
              id="select-all-devices"
              className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer"
              checked={allSelected}
              ref={(el) => {
                if (el) el.indeterminate = someSelected;
              }}
              onChange={(e) => handleSelectAll(e.target.checked)}
            />
          </TableHead>
          <TableHead
            className="cursor-pointer select-none"
            onClick={() => handleSort("hostname")}
          >
            <div className="flex items-center gap-1">
              Hostname
              <SortIcon direction={sortKey === "hostname" ? sortDirection : null} />
            </div>
          </TableHead>
          <TableHead
            className="cursor-pointer select-none"
            onClick={() => handleSort("mgmtIp")}
          >
            <div className="flex items-center gap-1">
              Management IP
              <SortIcon direction={sortKey === "mgmtIp" ? sortDirection : null} />
            </div>
          </TableHead>
          <TableHead
            className="cursor-pointer select-none"
            onClick={() => handleSort("vendor")}
          >
            <div className="flex items-center gap-1">
              Vendor
              <SortIcon direction={sortKey === "vendor" ? sortDirection : null} />
            </div>
          </TableHead>
          <TableHead
            className="cursor-pointer select-none"
            onClick={() => handleSort("platform")}
          >
            <div className="flex items-center gap-1">
              Platform
              <SortIcon direction={sortKey === "platform" ? sortDirection : null} />
            </div>
          </TableHead>
          <TableHead
            className="cursor-pointer select-none"
            onClick={() => handleSort("site")}
          >
            <div className="flex items-center gap-1">
              Site
              <SortIcon direction={sortKey === "site" ? sortDirection : null} />
            </div>
          </TableHead>
          <TableHead
            className="cursor-pointer select-none"
            onClick={() => handleSort("enabled")}
          >
            <div className="flex items-center gap-1">
              Status
              <SortIcon direction={sortKey === "enabled" ? sortDirection : null} />
            </div>
          </TableHead>
          <TableHead className="w-12">
            <span className="sr-only">Actions</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sortedRows.map((row) => (
          <TableRow key={row.id} className={cn(selectedIds.has(row.id) && "bg-muted/50")}>
            <TableCell>
              <input
                type="checkbox"
                className="device-checkbox h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary cursor-pointer"
                data-device-id={row.id}
                data-device-hostname={row.hostname}
                checked={selectedIds.has(row.id)}
                onChange={(e) => handleSelectOne(row.id, e.target.checked)}
              />
            </TableCell>
            <TableCell>
              <a
                href={row.detailUrl}
                className="font-medium text-primary hover:underline"
              >
                {row.hostname}
              </a>
            </TableCell>
            <TableCell>
              <code className="text-xs bg-muted px-2 py-1 rounded font-mono">
                {row.mgmtIp}
              </code>
            </TableCell>
            <TableCell>{row.vendor || "-"}</TableCell>
            <TableCell>{row.platform || "-"}</TableCell>
            <TableCell>
              {row.site ? (
                <Badge variant="secondary">{row.site}</Badge>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </TableCell>
            <TableCell>
              {row.enabled ? (
                <Badge variant="success" className="inline-flex items-center gap-1">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-3 w-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                  Enabled
                </Badge>
              ) : (
                <Badge variant="destructive" className="inline-flex items-center gap-1">
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className="h-3 w-3"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                  Disabled
                </Badge>
              )}
            </TableCell>
            <TableCell>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                    <span className="sr-only">Open menu</span>
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      className="h-4 w-4"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"
                      />
                    </svg>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem asChild>
                    <a href={row.detailUrl}>View Details</a>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <a href={`${row.detailUrl}#config`}>View Config</a>
                  </DropdownMenuItem>
                  <DropdownMenuItem asChild>
                    <a href={`${row.detailUrl}#jobs`}>View Jobs</a>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

export default DataTable;
