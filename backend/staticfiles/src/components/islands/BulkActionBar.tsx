import * as React from "react";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type BulkAction = {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost";
  disabled?: boolean;
};

export type BulkActionBarProps = {
  selectedCount: number;
  actions: BulkAction[];
  onClear: () => void;
  className?: string;
  position?: "bottom" | "top";
};

export function BulkActionBar({
  selectedCount,
  actions,
  onClear,
  className,
  position = "bottom",
}: BulkActionBarProps) {
  if (selectedCount === 0) return null;

  return (
    <div
      className={cn(
        "fixed left-1/2 z-50 -translate-x-1/2 transform",
        "flex items-center gap-3 rounded-lg border bg-background px-4 py-2 shadow-lg",
        position === "bottom" ? "bottom-6" : "top-20",
        className
      )}
    >
      {/* Selection count */}
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium">
          {selectedCount} {selectedCount === 1 ? "item" : "items"} selected
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onClear}
        >
          <X className="h-3.5 w-3.5" />
          <span className="sr-only">Clear selection</span>
        </Button>
      </div>

      {/* Divider */}
      <div className="h-6 w-px bg-border" />

      {/* Actions */}
      <div className="flex items-center gap-2">
        {actions.map((action, idx) => (
          <Button
            key={idx}
            variant={action.variant || "default"}
            size="sm"
            onClick={action.onClick}
            disabled={action.disabled}
          >
            {action.icon}
            {action.label}
          </Button>
        ))}
      </div>
    </div>
  );
}

// Hook for managing bulk selection state
export function useBulkSelection<T>(
  items: T[],
  getItemId: (item: T) => string | number
) {
  const [selectedIds, setSelectedIds] = React.useState<Set<string | number>>(
    new Set()
  );

  const toggleItem = React.useCallback((id: string | number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const toggleAll = React.useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === items.length) {
        return new Set();
      }
      return new Set(items.map(getItemId));
    });
  }, [items, getItemId]);

  const clear = React.useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const isSelected = React.useCallback(
    (id: string | number) => selectedIds.has(id),
    [selectedIds]
  );

  const selectedItems = React.useMemo(
    () => items.filter((item) => selectedIds.has(getItemId(item))),
    [items, selectedIds, getItemId]
  );

  return {
    selectedIds,
    selectedItems,
    selectedCount: selectedIds.size,
    isSelected,
    toggleItem,
    toggleAll,
    clear,
    isAllSelected: selectedIds.size === items.length && items.length > 0,
    isSomeSelected: selectedIds.size > 0 && selectedIds.size < items.length,
  };
}

export default BulkActionBar;
