import { useMemo, useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuthStore, selectCanModify } from '@/store/authStore'
import { apiClient } from '@/api/client'
import { toast } from 'sonner'
import { PageHeader } from '@/components/layout/page-header'
import { useJobs } from '../hooks/useJobs'
import { JobFilters } from './JobFilters'
import { JobTable } from './JobTable'
import { JobDetailsModal } from './JobDetailsModal'
import { normalizeJob } from '../utils'
import type { NormalizedJob } from '../types'

export function JobsView() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'
  const canModify = useAuthStore(selectCanModify)

  // Filter state
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter] = useState('all')
  const [textFilter, setTextFilter] = useState('')
  const [scope, setScope] = useState<'all' | 'mine'>(isAdmin ? 'all' : 'mine')

  // Modal state
  const [selectedJob, setSelectedJob] = useState<NormalizedJob | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Fetch jobs
  const { data, isLoading, error } = useJobs({
    filters: { status: statusFilter, type: typeFilter },
    scope,
    isAdmin,
    refetchInterval: 1000,
  })

  // Normalize and filter jobs
  const filteredJobs = useMemo(() => {
    if (!data) return []

    const normalized = data.map(normalizeJob)
    const query = textFilter.trim().toLowerCase()

    if (!query) return normalized

    return normalized.filter((job) => {
      return (
        `#${job.id}`.includes(query) ||
        job.type?.toLowerCase().includes(query) ||
        job.status?.toLowerCase().includes(query)
      )
    })
  }, [data, textFilter])

  const handleViewJob = (job: NormalizedJob) => {
    setSelectedJob(job)
    setIsModalOpen(true)
  }

  const handleRetryJob = async (job: NormalizedJob) => {
    try {
      const resp = await apiClient.retryJob(job.id)
      toast.success(`Job retry started: #${resp.job_id}`)
      // Open modal with the new job
      setSelectedJob({ ...job, id: resp.job_id, status: 'queued' })
      setIsModalOpen(true)
    } catch (err) {
      const error = err as Error
      toast.error(`Failed to retry job: ${error.message}`)
    }
  }

  const handleCancelJob = async (job: NormalizedJob) => {
    try {
      await apiClient.cancelJob(job.id)
      toast.success(`Job #${job.id} cancelled`)
    } catch (err) {
      const error = err as Error
      toast.error(`Failed to cancel job: ${error.message}`)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Jobs"
          description="View and manage automation job executions"
        />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (error) {
    return <div className="text-destructive p-4">Error loading jobs</div>
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Jobs"
        description="View and manage automation job executions"
      />

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <JobFilters
            statusFilter={statusFilter}
            typeFilter={typeFilter}
            textFilter={textFilter}
            scope={scope}
            isAdmin={isAdmin}
            onStatusChange={setStatusFilter}
            onTypeChange={setTypeFilter}
            onTextChange={setTextFilter}
            onScopeChange={setScope}
            totalJobs={filteredJobs.length}
          />
        </CardContent>
      </Card>

      {/* Jobs Table */}
      <Card>
        <CardContent className="p-0">
          <JobTable
            jobs={filteredJobs}
            isAdmin={isAdmin}
            scope={scope}
            canModify={canModify}
            onViewJob={handleViewJob}
            onRetryJob={handleRetryJob}
            onCancelJob={handleCancelJob}
          />
        </CardContent>
      </Card>

      {/* Job Details Modal */}
      <JobDetailsModal
        job={selectedJob}
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
      />
    </div>
  )
}
