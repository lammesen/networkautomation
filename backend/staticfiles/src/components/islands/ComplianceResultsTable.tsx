import { useMemo, useState } from "react";

import { Badge } from "../ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { cn } from "@/lib/utils";

type ResultRow = {
  id: number;
  policy: string;
  deviceId: number;
  deviceName: string;
  status: string;
  timestamp: string;
};

type SortKey = "id" | "policy" | "deviceName" | "status" | "timestamp";

type ResultsTableProps = {
  rows: ResultRow[];
  emptyState?: {
    title: string;
    description?: string;
  };
};

const sorters: Record<SortKey, (a: ResultRow, b: ResultRow) => number> = {
  id: (a, b) => a.id - b.id,
  policy: (a, b) => a.policy.localeCompare(b.policy),
  deviceName: (a, b) => a.deviceName.localeCompare(b.deviceName),
  status: (a, b) => a.status.localeCompare(b.status),
  timestamp: (a, b) => a.timestamp.localeCompare(b.timestamp),
};

export function ComplianceResultsTable({ rows, emptyState }: ResultsTableProps) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "timestamp", dir: "desc" });

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
    if (normalized === "pass") {
      return (
        <Badge className="gap-1 bg-emerald-600 text-white hover:bg-emerald-700">
          <span className="h-2 w-2 rounded-full bg-white" />
          {status}
        </Badge>
      );
    }
    if (normalized === "fail") {
      return (
        <Badge variant="destructive" className="gap-1">
          <span className="h-2 w-2 rounded-full bg-white/80" />
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
              d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <p className="text-base font-medium">{emptyState?.title || "No results"}</p>
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
            <SortableHead label="Result ID" sortKey="id" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Policy" sortKey="policy" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Device" sortKey="deviceName" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Status" sortKey="status" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Timestamp" sortKey="timestamp" activeSort={sort} onToggle={toggleSort} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedRows.map((row) => (
            <TableRow key={row.id} className="border-b transition-colors hover:bg-muted/50">
              <TableCell className="p-4 align-middle font-medium">#{row.id}</TableCell>
              <TableCell className="p-4 align-middle">{row.policy}</TableCell>
              <TableCell className="p-4 align-middle">
                <a href={`/devices/${row.deviceId}/`} className="font-medium text-primary hover:underline">
                  {row.deviceName}
                </a>
              </TableCell>
              <TableCell className="p-4 align-middle">{renderStatus(row.status)}</TableCell>
              <TableCell className="p-4 align-middle text-sm text-muted-foreground">{row.timestamp}</TableCell>
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
      className={cn(
        "h-12 px-4 text-left align-middle font-medium text-muted-foreground cursor-pointer select-none",
        isActive ? "text-foreground" : ""
      )}
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
  return direction === "asc" ? <span className="text-muted-foreground">↑</span> : <span className="text-muted-foreground">↓</span>;
}

export default ComplianceResultsTable;
