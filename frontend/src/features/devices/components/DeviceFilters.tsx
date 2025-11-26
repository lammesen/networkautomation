import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChevronDown } from 'lucide-react'
import { DeviceSearchField, deviceSearchFieldOptions } from '../types'

interface DeviceFiltersProps {
  search: string
  searchFields: DeviceSearchField[]
  showDisabled: boolean
  onChange: (values: Partial<{ search: string; searchFields: DeviceSearchField[]; showDisabled: boolean }>) => void
}

export function DeviceFilters({ search, searchFields, showDisabled, onChange }: DeviceFiltersProps) {
  const toggleField = (field: DeviceSearchField, enabled: boolean) => {
    const next = enabled ? [...searchFields, field] : searchFields.filter((f) => f !== field)
    onChange({ searchFields: next })
  }

  return (
    <div className="flex gap-3 flex-wrap items-center">
      <Input
        className="min-w-[260px] max-w-[400px]"
        placeholder="Search devices..."
        value={search}
        onChange={(e) => onChange({ search: e.target.value })}
      />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-2">
            Fields ({searchFields.length})
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuLabel>Search fields</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {deviceSearchFieldOptions.map(({ key, label }) => (
            <DropdownMenuCheckboxItem
              key={key}
              checked={searchFields.includes(key)}
              onCheckedChange={(checked) => toggleField(key, Boolean(checked))}
            >
              {label}
            </DropdownMenuCheckboxItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      <label className="flex items-center gap-2 select-none">
        <input
          id="showDisabled"
          type="checkbox"
          className="h-4 w-4"
          checked={showDisabled}
          onChange={(e) => onChange({ showDisabled: e.target.checked })}
        />
        <Label htmlFor="showDisabled" className="text-sm text-muted-foreground cursor-pointer">
          Show disabled
        </Label>
      </label>
    </div>
  )
}
