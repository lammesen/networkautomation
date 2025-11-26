import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/status-badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { MoreHorizontal, RotateCcw, ScrollText } from 'lucide-react'
import { formatDateTime } from '@/lib/formatters'
import type { NormalizedJob } from '../types'
import { formatJobType, canRetryJob } from '../utils'

interface JobTableProps {
  jobs: NormalizedJob[]
  isAdmin: boolean
  scope: 'all' | 'mine'
  onViewJob: (job: NormalizedJob) => void
  onRetryJob: (job: NormalizedJob) => void
}

export function JobTable({ jobs, isAdmin, scope, onViewJob, onRetryJob }: JobTableProps) {
  const showAdminColumns = isAdmin && scope === 'all'

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>ID</TableHead>
          {showAdminColumns && <TableHead>Customer</TableHead>}
          {showAdminColumns && <TableHead>User</TableHead>}
          <TableHead>Type</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Started</TableHead>
          <TableHead>Finished</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.length > 0 ? (
          jobs.map((job) => {
            const canRetry = canRetryJob(job)

            return (
              <TableRow key={job.id}>
                <TableCell className="font-medium">#{job.id}</TableCell>
                {showAdminColumns && <TableCell>{job.customer_id ?? '-'}</TableCell>}
                {showAdminColumns && <TableCell>{job.user_id ?? '-'}</TableCell>}
                <TableCell>{formatJobType(job.type)}</TableCell>
                <TableCell>
                  <StatusBadge status={job.status} />
                </TableCell>
                <TableCell>{formatDateTime(job.started_at)}</TableCell>
                <TableCell>{formatDateTime(job.finished_at)}</TableCell>
                <TableCell className="text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                        <span className="sr-only">Open actions</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-44">
                      <DropdownMenuLabel>Job actions</DropdownMenuLabel>
                      <DropdownMenuItem onSelect={() => onViewJob(job)}>
                        <ScrollText className="h-4 w-4 mr-2" />
                        View output
                      </DropdownMenuItem>
                      {canRetry && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onSelect={() => onRetryJob(job)}>
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Retry job
                          </DropdownMenuItem>
                        </>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            )
          })
        ) : (
          <TableRow>
            <TableCell
              colSpan={showAdminColumns ? 8 : 6}
              className="text-center h-24 text-muted-foreground"
            >
              No jobs found
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}
