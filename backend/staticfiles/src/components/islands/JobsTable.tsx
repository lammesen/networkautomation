import { useMemo, useState } from "react";

import { Badge } from "../ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../ui/table";
import { cn } from "@/lib/utils";

type JobRow = {
  id: number;
  type: string;
  status: string;
  user: string;
  customer: string;
  requestedAt: string;
  detailUrl: string;
};

type SortKey = "id" | "type" | "status" | "user" | "customer" | "requestedAt";

type JobsTableProps = {
  rows: JobRow[];
  emptyState?: {
    title: string;
    description?: string;
  };
};

const sorters: Record<SortKey, (a: JobRow, b: JobRow) => number> = {
  id: (a, b) => a.id - b.id,
  type: (a, b) => a.type.localeCompare(b.type),
  status: (a, b) => a.status.localeCompare(b.status),
  user: (a, b) => a.user.localeCompare(b.user),
  customer: (a, b) => a.customer.localeCompare(b.customer),
  requestedAt: (a, b) => a.requestedAt.localeCompare(b.requestedAt),
};

export function JobsTable({ rows, emptyState }: JobsTableProps) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "requestedAt",
    dir: "desc",
  });

  const sortedRows = useMemo(() => {
    const sorted = [...rows].sort(sorters[sort.key]);
    if (sort.dir === "desc") sorted.reverse();
    return sorted;
  }, [rows, sort]);

  const toggleSort = (key: SortKey) => {
    setSort((prev) =>
      prev.key === key ? { key, dir: prev.dir === "asc" ? "desc" : "asc" } : { key, dir: "asc" }
    );
  };

  const renderStatus = (status: string) => {
    const normalized = status.toLowerCase();
    if (normalized === "success") {
      return (
        <Badge className="gap-1 bg-emerald-600 text-white hover:bg-emerald-700">
          <span className="h-2 w-2 rounded-full bg-white" />
          {status}
        </Badge>
      );
    }
    if (normalized === "running") {
      return (
        <Badge className="gap-1 bg-primary/10 text-primary">
          <span className="h-2 w-2 animate-pulse rounded-full bg-primary" />
          {status}
        </Badge>
      );
    }
    if (normalized === "failed") {
      return (
        <Badge variant="destructive" className="gap-1">
          <span className="h-2 w-2 rounded-full bg-white/80" />
          {status}
        </Badge>
      );
    }
    if (normalized === "pending") {
      return (
        <Badge className="gap-1 bg-amber-200 text-amber-900">
          <span className="h-2 w-2 rounded-full bg-amber-900/70" />
          {status}
        </Badge>
      );
    }
    return <Badge variant="secondary">{status}</Badge>;
  };

  if (!sortedRows.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center text-muted-foreground">
        <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-muted">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-6 w-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="1.5"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </div>
        <p className="text-base font-medium">{emptyState?.title || "No jobs"}</p>
        {emptyState?.description ? (
          <p className="text-sm text-muted-foreground">{emptyState.description}</p>
        ) : null}
      </div>
    );
  }

  return (
    <div className="relative w-full overflow-auto">
      <Table>
        <TableHeader>
          <TableRow className="border-b transition-colors">
            <SortableHead label="Job ID" sortKey="id" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Type" sortKey="type" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Status" sortKey="status" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="User" sortKey="user" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Customer" sortKey="customer" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Requested" sortKey="requestedAt" activeSort={sort} onToggle={toggleSort} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedRows.map((row) => (
            <TableRow key={row.id} className="border-b transition-colors hover:bg-muted/50">
              <TableCell className="p-4 align-middle">
                <a href={row.detailUrl} className="font-medium text-primary hover:underline">
                  #{row.id}
                </a>
              </TableCell>
              <TableCell className="p-4 align-middle">
                <Badge variant="secondary">{row.type}</Badge>
              </TableCell>
              <TableCell className="p-4 align-middle">{renderStatus(row.status)}</TableCell>
              <TableCell className="p-4 align-middle text-sm">{row.user}</TableCell>
              <TableCell className="p-4 align-middle">
                <Badge variant="outline">{row.customer}</Badge>
              </TableCell>
              <TableCell className="p-4 align-middle text-sm text-muted-foreground">
                {row.requestedAt}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

type SortableHeadProps = {
  label: string;
  sortKey: SortKey;
  activeSort: { key: SortKey; dir: "asc" | "desc" };
  onToggle: (key: SortKey) => void;
};

function SortableHead({ label, sortKey, activeSort, onToggle }: SortableHeadProps) {
  const isActive = activeSort.key === sortKey;
  return (
    <TableHead
      className={cn("h-12 px-4 text-left align-middle font-medium text-muted-foreground cursor-pointer select-none", isActive ? "text-foreground" : "")}
      aria-sort={isActive ? (activeSort.dir === "asc" ? "ascending" : "descending") : "none"}
      onClick={() => onToggle(sortKey)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <SortIcon direction={isActive ? activeSort.dir : undefined} />
      </span>
    </TableHead>
  );
}

function SortIcon({ direction }: { direction?: "asc" | "desc" }) {
  if (!direction) return <span className="text-muted-foreground">↕</span>;
  return direction === "asc" ? (
    <span className="text-muted-foreground">↑</span>
  ) : (
    <span className="text-muted-foreground">↓</span>
  );
}

export default JobsTable;
