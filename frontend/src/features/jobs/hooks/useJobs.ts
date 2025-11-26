import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import type { Job, JobFilters } from '../types'

export const jobKeys = {
  all: ['jobs'] as const,
  lists: () => [...jobKeys.all, 'list'] as const,
  list: (filters: JobFilters & { scope?: 'all' | 'mine' }) => [...jobKeys.lists(), filters] as const,
  details: () => [...jobKeys.all, 'detail'] as const,
  detail: (id: number) => [...jobKeys.details(), id] as const,
  logs: (id: number) => [...jobKeys.detail(id), 'logs'] as const,
}

interface UseJobsOptions {
  filters: JobFilters
  scope: 'all' | 'mine'
  isAdmin: boolean
  refetchInterval?: number
}

export function useJobs({ filters, scope, isAdmin, refetchInterval = 1000 }: UseJobsOptions) {
  return useQuery({
    queryKey: jobKeys.list({ ...filters, scope }),
    queryFn: async (): Promise<Job[]> => {
      const params = {
        status: filters.status !== 'all' ? filters.status : undefined,
        type: filters.type !== 'all' ? filters.type : undefined,
        limit: filters.limit,
      }

      if (isAdmin && scope === 'all') {
        try {
          return await apiClient.getAdminJobs({ ...params, limit: params.limit ?? 200 })
        } catch (err: unknown) {
          // Some deployments may disable the admin endpoint; fall back to user-scoped jobs
          const error = err as { response?: { status?: number } }
          if (error?.response?.status === 422 || error?.response?.status === 404) {
            return apiClient.getJobs(params)
          }
          throw err
        }
      }
      return apiClient.getJobs(params)
    },
    refetchInterval,
  })
}

export function useJob(id: number) {
  return useQuery({
    queryKey: jobKeys.detail(id),
    queryFn: () => apiClient.getJob(id),
    enabled: !!id,
  })
}

export function useJobLogs(id: number, isAdmin: boolean) {
  return useQuery({
    queryKey: jobKeys.logs(id),
    queryFn: () => (isAdmin ? apiClient.getAdminJobLogs(id) : apiClient.getJobLogs(id)),
    enabled: !!id,
  })
}
