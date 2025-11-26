import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChevronDown, Search, SlidersHorizontal } from 'lucide-react'
import { type DeviceSearchField, deviceSearchFieldOptions } from '../types'

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
      <div className="relative flex-1 min-w-[260px] max-w-[400px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          className="pl-9"
          placeholder="Search devices..."
          value={search}
          onChange={(e) => onChange({ search: e.target.value })}
        />
      </div>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="default" className="gap-2">
            <SlidersHorizontal className="h-4 w-4" />
            Fields
            <span className="ml-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
              {searchFields.length}
            </span>
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuLabel>Search in these fields</DropdownMenuLabel>
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

      <div className="flex items-center gap-2 ml-2">
        <Checkbox
          id="showDisabled"
          checked={showDisabled}
          onCheckedChange={(checked) => onChange({ showDisabled: checked === true })}
        />
        <Label htmlFor="showDisabled" className="text-sm text-muted-foreground cursor-pointer select-none">
          Include disabled devices
        </Label>
      </div>
    </div>
  )
}
