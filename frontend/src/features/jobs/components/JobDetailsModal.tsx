import { useMemo } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { StatusBadge } from '@/components/ui/status-badge'
import { JobLiveLogs } from './JobLiveLogs'
import { JobSummaryCard } from './JobSummaryCard'
import { JobHostResults } from './JobHostResults'
import { useJobWebSocket } from '../hooks/useJobWebSocket'
import { parseResults, calculateHostCounts } from '../utils'
import type { NormalizedJob, JobHostResult } from '../types'

interface JobDetailsModalProps {
  job: NormalizedJob | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function JobDetailsModal({ job, open, onOpenChange }: JobDetailsModalProps) {
  const { logs, status, clearLogs } = useJobWebSocket({
    jobId: job?.id ?? null,
    enabled: open && !!job,
  })

  // Clear logs when modal opens with a new job
  const handleOpenChange = (isOpen: boolean) => {
    if (isOpen && job) {
      clearLogs()
    }
    onOpenChange(isOpen)
  }

  const summary = useMemo(() => parseResults(job?.result_summary_json), [job])
  const hostResults = (summary?.results || summary?.diffs) as Record<string, JobHostResult> | undefined
  const hostCounts = useMemo(() => calculateHostCounts(hostResults), [hostResults])

  const displayStatus = status || job?.status

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-[95vw] max-h-[95vh]" aria-describedby="job-details-description">
        <DialogHeader>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div>
              <DialogTitle>Job #{job?.id}</DialogTitle>
              <DialogDescription id="job-details-description">
                Results per device and live logs
              </DialogDescription>
            </div>
            {displayStatus && <StatusBadge status={displayStatus} />}
          </div>
        </DialogHeader>

        <ScrollArea className="h-[80vh] w-full rounded-md border p-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <JobLiveLogs logs={logs} status={status || job?.status || null} />
            <JobSummaryCard
              hostCounts={hostCounts}
              total={summary?.total}
              success={summary?.success}
              succeeded={summary?.succeeded}
              failed={summary?.failed}
              partial={summary?.partial}
              running={summary?.running}
              payload={job?.payload_json ?? null}
            />
          </div>

          <div className="mt-4 space-y-3">
            {hostResults && Object.keys(hostResults).length > 0 ? (
              <JobHostResults hostResults={hostResults} />
            ) : (
              <div className="text-muted-foreground text-sm">No per-device results captured.</div>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
