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

type SnapshotRow = {
  id: number;
  deviceId: number;
  deviceName: string;
  source: string;
  createdAt: string;
  hash: string;
};

type SortKey = "id" | "deviceName" | "source" | "createdAt";

type SnapshotsTableProps = {
  rows: SnapshotRow[];
  emptyState?: {
    title: string;
    description?: string;
  };
};

const sorters: Record<SortKey, (a: SnapshotRow, b: SnapshotRow) => number> = {
  id: (a, b) => a.id - b.id,
  deviceName: (a, b) => a.deviceName.localeCompare(b.deviceName),
  source: (a, b) => a.source.localeCompare(b.source),
  createdAt: (a, b) => a.createdAt.localeCompare(b.createdAt),
};

export function SnapshotsTable({ rows, emptyState }: SnapshotsTableProps) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "createdAt",
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
              d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
            />
          </svg>
        </div>
        <p className="text-base font-medium">{emptyState?.title || "No snapshots"}</p>
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
            <SortableHead label="Snapshot ID" sortKey="id" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Device" sortKey="deviceName" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Source" sortKey="source" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Created" sortKey="createdAt" activeSort={sort} onToggle={toggleSort} />
            <TableHead className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">
              Hash
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedRows.map((row) => (
            <TableRow key={row.id} className="border-b transition-colors hover:bg-muted/50">
              <TableCell className="p-4 align-middle font-medium">#{row.id}</TableCell>
              <TableCell className="p-4 align-middle">
                <a href={`/devices/${row.deviceId}/`} className="font-medium text-primary hover:underline">
                  {row.deviceName}
                </a>
              </TableCell>
              <TableCell className="p-4 align-middle">
                <Badge variant="secondary">{row.source}</Badge>
              </TableCell>
              <TableCell className="p-4 align-middle text-sm text-muted-foreground">{row.createdAt}</TableCell>
              <TableCell className="p-4 align-middle">
                <code className="text-xs bg-muted px-2 py-1 rounded font-mono">{row.hash}</code>
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
  return direction === "asc" ? (
    <span className="text-muted-foreground">↑</span>
  ) : (
    <span className="text-muted-foreground">↓</span>
  );
}

export default SnapshotsTable;
