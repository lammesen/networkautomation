import * as React from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export type FilterOption = {
  label: string;
  value: string;
};

export type FilterDef = {
  id: string;
  label: string;
  type: "select" | "search";
  options?: FilterOption[];
  placeholder?: string;
};

export type FilterValues = Record<string, string>;

export type FilterBarProps = {
  filters: FilterDef[];
  values: FilterValues;
  onChange: (values: FilterValues) => void;
  onClear?: () => void;
  className?: string;
};

export function FilterBar({
  filters,
  values,
  onChange,
  onClear,
  className,
}: FilterBarProps) {
  const activeFilterCount = Object.values(values).filter(Boolean).length;

  const handleChange = (id: string, value: string) => {
    onChange({ ...values, [id]: value });
  };

  const handleClear = () => {
    const cleared: FilterValues = {};
    filters.forEach((f) => {
      cleared[f.id] = "";
    });
    onChange(cleared);
    onClear?.();
  };

  return (
    <div className={cn("flex flex-wrap items-center gap-2", className)}>
      {filters.map((filter) => {
        if (filter.type === "search") {
          return (
            <div key={filter.id} className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder={filter.placeholder || `Search ${filter.label.toLowerCase()}...`}
                value={values[filter.id] || ""}
                onChange={(e) => handleChange(filter.id, e.target.value)}
                className="pl-8 w-[200px]"
              />
            </div>
          );
        }

        if (filter.type === "select" && filter.options) {
          return (
            <Select
              key={filter.id}
              value={values[filter.id] || ""}
              onValueChange={(value) => handleChange(filter.id, value)}
            >
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder={filter.placeholder || filter.label} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All {filter.label}</SelectItem>
                {filter.options.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          );
        }

        return null;
      })}

      {activeFilterCount > 0 && (
        <Button
          variant="ghost"
          size="sm"
          onClick={handleClear}
          className="h-8 px-2 lg:px-3"
        >
          Clear
          <Badge variant="secondary" className="ml-1.5 h-5 px-1.5">
            {activeFilterCount}
          </Badge>
          <X className="ml-1 h-3 w-3" />
        </Button>
      )}
    </div>
  );
}

// Hook for managing filter state with URL sync
export function useFilters(
  filters: FilterDef[],
  options?: { syncToUrl?: boolean }
) {
  const [values, setValues] = React.useState<FilterValues>(() => {
    const initial: FilterValues = {};
    filters.forEach((f) => {
      initial[f.id] = "";
    });

    // Initialize from URL if syncing
    if (options?.syncToUrl && typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      filters.forEach((f) => {
        const urlValue = params.get(f.id);
        if (urlValue) {
          initial[f.id] = urlValue;
        }
      });
    }

    return initial;
  });

  const handleChange = React.useCallback(
    (newValues: FilterValues) => {
      setValues(newValues);

      // Sync to URL if enabled
      if (options?.syncToUrl && typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        Object.entries(newValues).forEach(([key, value]) => {
          if (value) {
            params.set(key, value);
          } else {
            params.delete(key);
          }
        });
        const newUrl = `${window.location.pathname}${params.toString() ? `?${params.toString()}` : ""}`;
        window.history.replaceState({}, "", newUrl);
      }
    },
    [options?.syncToUrl]
  );

  const clear = React.useCallback(() => {
    const cleared: FilterValues = {};
    filters.forEach((f) => {
      cleared[f.id] = "";
    });
    handleChange(cleared);
  }, [filters, handleChange]);

  return { values, onChange: handleChange, clear };
}

export default FilterBar;
