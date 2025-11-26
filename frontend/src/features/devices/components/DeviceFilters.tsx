import { useState, useRef, useEffect } from 'react'
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
import { ChevronDown, Search, SlidersHorizontal, History } from 'lucide-react'
import { type DeviceSearchField, deviceSearchFieldOptions } from '../types'
import { useUIStore } from '@/store/uiStore'
import { cn } from '@/lib/utils'

interface DeviceFiltersProps {
  search: string
  searchFields: DeviceSearchField[]
  showDisabled: boolean
  onChange: (values: Partial<{ search: string; searchFields: DeviceSearchField[]; showDisabled: boolean }>) => void
}

export function DeviceFilters({ search, searchFields, showDisabled, onChange }: DeviceFiltersProps) {
  const [showRecent, setShowRecent] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const { recentDeviceSearches, addRecentSearch, clearRecentSearches } = useUIStore()

  const toggleField = (field: DeviceSearchField, enabled: boolean) => {
    const next = enabled ? [...searchFields, field] : searchFields.filter((f) => f !== field)
    onChange({ searchFields: next })
  }

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowRecent(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSearchSubmit = () => {
    if (search.trim()) {
      addRecentSearch(search.trim())
    }
    setShowRecent(false)
  }

  const handleSelectRecent = (query: string) => {
    onChange({ search: query })
    setShowRecent(false)
    addRecentSearch(query)
  }

  return (
    <div className="flex gap-3 flex-wrap items-center">
      <div className="relative flex-1 min-w-[260px] max-w-[400px]">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          ref={inputRef}
          className="pl-9"
          placeholder="Search devices..."
          value={search}
          onChange={(e) => onChange({ search: e.target.value })}
          onFocus={() => recentDeviceSearches.length > 0 && setShowRecent(true)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              handleSearchSubmit()
            }
            if (e.key === 'Escape') {
              setShowRecent(false)
            }
          }}
        />
        {/* Recent searches dropdown */}
        {showRecent && recentDeviceSearches.length > 0 && (
          <div
            ref={dropdownRef}
            className="absolute top-full left-0 right-0 mt-1 bg-popover border rounded-md shadow-md z-50"
          >
            <div className="flex items-center justify-between px-3 py-2 border-b">
              <span className="text-xs font-medium text-muted-foreground">Recent searches</span>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs text-muted-foreground hover:text-foreground"
                onClick={() => {
                  clearRecentSearches()
                  setShowRecent(false)
                }}
              >
                Clear
              </Button>
            </div>
            <div className="py-1">
              {recentDeviceSearches.map((query, i) => (
                <button
                  key={i}
                  className={cn(
                    'flex items-center gap-2 w-full px-3 py-2 text-sm text-left',
                    'hover:bg-accent hover:text-accent-foreground',
                    'focus:bg-accent focus:text-accent-foreground focus:outline-none'
                  )}
                  onClick={() => handleSelectRecent(query)}
                >
                  <History className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="truncate">{query}</span>
                </button>
              ))}
            </div>
          </div>
        )}
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
