import { useMemo, useState } from "react";

import { Badge } from "../ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { cn } from "@/lib/utils";

type LinkRow = {
  id: number;
  localDeviceId: number;
  localDevice: string;
  localInterface: string;
  remoteHost: string;
  remoteInterface: string;
  protocol: string;
};

type SortKey = "localDevice" | "localInterface" | "remoteHost" | "remoteInterface" | "protocol";

type TopologyTableProps = {
  rows: LinkRow[];
  emptyState?: {
    title: string;
    description?: string;
  };
};

const sorters: Record<SortKey, (a: LinkRow, b: LinkRow) => number> = {
  localDevice: (a, b) => a.localDevice.localeCompare(b.localDevice),
  localInterface: (a, b) => a.localInterface.localeCompare(b.localInterface),
  remoteHost: (a, b) => a.remoteHost.localeCompare(b.remoteHost),
  remoteInterface: (a, b) => a.remoteInterface.localeCompare(b.remoteInterface),
  protocol: (a, b) => a.protocol.localeCompare(b.protocol),
};

export function TopologyTable({ rows, emptyState }: TopologyTableProps) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({ key: "localDevice", dir: "asc" });

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
              d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
            />
          </svg>
        </div>
        <p className="text-base font-medium">{emptyState?.title || "No topology links"}</p>
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
            <SortableHead label="Local Device" sortKey="localDevice" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Local Interface" sortKey="localInterface" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Remote Host" sortKey="remoteHost" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Remote Interface" sortKey="remoteInterface" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Protocol" sortKey="protocol" activeSort={sort} onToggle={toggleSort} />
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedRows.map((row) => (
            <TableRow key={row.id} className="border-b transition-colors hover:bg-muted/50">
              <TableCell className="p-4 align-middle">
                <a href={`/devices/${row.localDeviceId}/`} className="font-medium text-primary hover:underline">
                  {row.localDevice}
                </a>
              </TableCell>
              <TableCell className="p-4 align-middle">
                <code className="text-xs bg-muted px-2 py-1 rounded font-mono">{row.localInterface}</code>
              </TableCell>
              <TableCell className="p-4 align-middle font-medium">{row.remoteHost}</TableCell>
              <TableCell className="p-4 align-middle">
                <code className="text-xs bg-muted px-2 py-1 rounded font-mono">{row.remoteInterface}</code>
              </TableCell>
              <TableCell className="p-4 align-middle">
                <Badge variant="secondary">{row.protocol}</Badge>
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
  return direction === "asc" ? <span className="text-muted-foreground">↑</span> : <span className="text-muted-foreground">↓</span>;
}

export default TopologyTable;
