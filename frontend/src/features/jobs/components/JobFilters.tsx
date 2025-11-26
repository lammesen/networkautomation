import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

interface JobFiltersProps {
  statusFilter: string
  typeFilter: string
  textFilter: string
  scope: 'all' | 'mine'
  isAdmin: boolean
  onStatusChange: (value: string) => void
  onTypeChange: (value: string) => void
  onTextChange: (value: string) => void
  onScopeChange: (value: 'all' | 'mine') => void
  totalJobs: number
}

export function JobFilters({
  statusFilter,
  typeFilter,
  textFilter,
  scope,
  isAdmin,
  onStatusChange,
  onTypeChange,
  onTextChange,
  onScopeChange,
  totalJobs,
}: JobFiltersProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Input
        placeholder="Search by ID, type, or status"
        className="w-full sm:w-[260px]"
        value={textFilter}
        onChange={(e) => onTextChange(e.target.value)}
      />

      <div className="flex gap-2 flex-wrap">
        <Select value={statusFilter} onValueChange={onStatusChange}>
          <SelectTrigger className="w-[170px]">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Statuses</SelectItem>
            <SelectItem value="scheduled">Scheduled</SelectItem>
            <SelectItem value="queued">Queued</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="success">Success</SelectItem>
            <SelectItem value="partial">Partial</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
          </SelectContent>
        </Select>

        <Select value={typeFilter} onValueChange={onTypeChange}>
          <SelectTrigger className="w-[170px]">
            <SelectValue placeholder="All Types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Types</SelectItem>
            <SelectItem value="run_commands">Run Commands</SelectItem>
            <SelectItem value="config_backup">Config Backup</SelectItem>
            <SelectItem value="config_deploy_preview">Config Deploy Preview</SelectItem>
            <SelectItem value="config_deploy_commit">Config Deploy Commit</SelectItem>
            <SelectItem value="compliance_check">Compliance Check</SelectItem>
          </SelectContent>
        </Select>

        {isAdmin && (
          <Select value={scope} onValueChange={onScopeChange}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Scope" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All jobs</SelectItem>
              <SelectItem value="mine">My jobs</SelectItem>
            </SelectContent>
          </Select>
        )}
      </div>

      <div className="ml-auto text-sm text-muted-foreground">
        Showing {totalJobs} {totalJobs === 1 ? 'job' : 'jobs'}
      </div>
    </div>
  )
}
