import { Input } from '@/components/ui/input'

interface DeviceFiltersProps {
  search: string
  site: string
  role: string
  onChange: (values: Partial<Record<'search' | 'site' | 'role', string>>) => void
}

export function DeviceFilters({ search, site, role, onChange }: DeviceFiltersProps) {
  return (
    <div className="flex gap-4 flex-wrap">
      <Input
        className="max-w-[300px]"
        placeholder="Search hostname or IP..."
        value={search}
        onChange={(e) => onChange({ search: e.target.value })}
      />
      <Input
        className="max-w-[200px]"
        placeholder="Filter by site..."
        value={site}
        onChange={(e) => onChange({ site: e.target.value })}
      />
      <Input
        className="max-w-[200px]"
        placeholder="Filter by role..."
        value={role}
        onChange={(e) => onChange({ role: e.target.value })}
      />
    </div>
  )
}


