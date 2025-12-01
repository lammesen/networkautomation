import { useMemo, useState } from "react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/table";
import { cn } from "@/lib/utils";

type PolicyRow = {
  id: number;
  name: string;
  customer: string;
  updatedAt: string;
  runUrl: string;
};

type SortKey = "name" | "customer" | "updatedAt";

type PoliciesTableProps = {
  rows: PolicyRow[];
  emptyState?: {
    title: string;
    description?: string;
  };
};

const sorters: Record<SortKey, (a: PolicyRow, b: PolicyRow) => number> = {
  name: (a, b) => a.name.localeCompare(b.name),
  customer: (a, b) => a.customer.localeCompare(b.customer),
  updatedAt: (a, b) => a.updatedAt.localeCompare(b.updatedAt),
};

export function CompliancePoliciesTable({ rows, emptyState }: PoliciesTableProps) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "name",
    dir: "asc",
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

  const runPolicy = async (row: PolicyRow) => {
    const htmx = (window as any).htmx;
    if (htmx?.ajax) {
      htmx.ajax("POST", row.runUrl, { target: `#policy-run-${row.id}`, swap: "innerHTML" });
      window.dispatchEvent(
        new CustomEvent("webnet:toast", { detail: { message: `Started policy ${row.name}`, variant: "success" } })
      );
    }
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
              d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"
            />
          </svg>
        </div>
        <p className="text-base font-medium">{emptyState?.title || "No policies"}</p>
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
            <SortableHead label="Policy Name" sortKey="name" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Customer" sortKey="customer" activeSort={sort} onToggle={toggleSort} />
            <SortableHead label="Last Updated" sortKey="updatedAt" activeSort={sort} onToggle={toggleSort} />
            <TableHead className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sortedRows.map((row) => (
            <TableRow key={row.id} className="border-b transition-colors hover:bg-muted/50">
              <TableCell className="p-4 align-middle font-medium">{row.name}</TableCell>
              <TableCell className="p-4 align-middle">
                <Badge variant="outline">{row.customer}</Badge>
              </TableCell>
              <TableCell className="p-4 align-middle text-sm text-muted-foreground">{row.updatedAt}</TableCell>
              <TableCell className="p-4 align-middle text-right">
                <div id={`policy-run-${row.id}`} className="inline-block"></div>
                <Button size="sm" className="h-7 px-2.5" onClick={() => runPolicy(row)}>
                  Run
                </Button>
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

export default CompliancePoliciesTable;
