import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/status-badge'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
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
import { MoreHorizontal, RotateCcw, ScrollText, Clock, XCircle } from 'lucide-react'
import { formatDateTime } from '@/lib/formatters'
import type { NormalizedJob } from '../types'
import { formatJobType, canRetryJob } from '../utils'

interface JobTableProps {
  jobs: NormalizedJob[]
  isAdmin: boolean
  scope: 'all' | 'mine'
  canModify?: boolean
  onViewJob: (job: NormalizedJob) => void
  onRetryJob: (job: NormalizedJob) => void
  onCancelJob?: (job: NormalizedJob) => void
}

export function JobTable({ jobs, isAdmin, scope, canModify = true, onViewJob, onRetryJob, onCancelJob }: JobTableProps) {
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
          <TableHead>Scheduled</TableHead>
          <TableHead>Started</TableHead>
          <TableHead>Finished</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.length > 0 ? (
          jobs.map((job) => {
            const canRetry = canRetryJob(job)
            const canCancel = job.status === 'scheduled' || job.status === 'queued'
            const isScheduled = job.status === 'scheduled' && job.scheduled_for

            return (
              <TableRow key={job.id} className={isScheduled ? 'bg-amber-50/50 dark:bg-amber-950/20' : ''}>
                <TableCell className="font-medium">#{job.id}</TableCell>
                {showAdminColumns && <TableCell>{job.customer_id ?? '-'}</TableCell>}
                {showAdminColumns && <TableCell>{job.user_id ?? '-'}</TableCell>}
                <TableCell>{formatJobType(job.type)}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={job.status} />
                    {isScheduled && (
                      <Tooltip>
                        <TooltipTrigger>
                          <Badge variant="outline" className="text-xs gap-1">
                            <Clock className="h-3 w-3" />
                            Pending
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent>
                          Scheduled for {formatDateTime(job.scheduled_for)}
                        </TooltipContent>
                      </Tooltip>
                    )}
                  </div>
                </TableCell>
                <TableCell>
                  {job.scheduled_for ? (
                    <span className={isScheduled ? 'text-amber-600 dark:text-amber-400 font-medium' : ''}>
                      {formatDateTime(job.scheduled_for)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
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
                      {canRetry && canModify && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onSelect={() => onRetryJob(job)}>
                            <RotateCcw className="h-4 w-4 mr-2" />
                            Retry job
                          </DropdownMenuItem>
                        </>
                      )}
                      {canCancel && onCancelJob && canModify && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            onSelect={() => onCancelJob(job)}
                            className="text-destructive focus:text-destructive"
                          >
                            <XCircle className="h-4 w-4 mr-2" />
                            Cancel job
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
              colSpan={showAdminColumns ? 9 : 7}
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
