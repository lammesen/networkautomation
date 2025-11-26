import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Table,
  TableBody,
  TableHead,
  TableHeader,
  TableRow,
  TableCell,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { DateTimePicker } from '@/components/ui/date-time-picker'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusBadge } from '@/components/ui/status-badge'
import { PageHeader } from '@/components/layout/page-header'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { formatDateTime } from '@/lib/formatters'
import { Plus, Play, ShieldCheck, FileCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PolicyBuilderDialog } from '@/features/compliance'
import type { CompliancePolicyCreate, ComplianceResult, CompliancePolicyStats } from '@/types'
import { useAuthStore, selectCanModify } from '@/store/authStore'

export default function CompliancePage() {
  const canModify = useAuthStore(selectCanModify)
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [createError, setCreateError] = useState('')
  const [filters, setFilters] = useState<{
    policyId: string
    deviceId: string
    status: string
    start: Date | undefined
    end: Date | undefined
  }>({
    policyId: '',
    deviceId: '',
    status: '',
    start: undefined,
    end: undefined,
  })
  const [debouncedFilters, setDebouncedFilters] = useState(filters)
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(20)
  const [detailOpen, setDetailOpen] = useState(false)
  const [detailError, setDetailError] = useState('')

  const queryClient = useQueryClient()

  useEffect(() => {
    const handle = setTimeout(() => setDebouncedFilters(filters), 300)
    return () => clearTimeout(handle)
  }, [filters])

  const {
    data: overview,
    isLoading: isLoadingOverview,
    error: overviewError,
    refetch: refetchOverview,
  } = useQuery({
    queryKey: ['complianceOverview'],
    queryFn: () => apiClient.getComplianceOverview(),
  })

  const createPolicyMutation = useMutation({
    mutationFn: (data: CompliancePolicyCreate) => apiClient.createCompliancePolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['complianceOverview'] })
      setIsCreateModalOpen(false)
      setCreateError('')
      toast.success('Policy created')
    },
    onError: (err: Error & { data?: { detail?: string } }) => {
      const msg = err.data?.detail || err.message || 'Failed to create policy'
      setCreateError(msg)
      toast.error(msg)
    },
  })

  const runComplianceMutation = useMutation({
    mutationFn: (policyId: number) => apiClient.runComplianceCheck(policyId),
    onSuccess: () => {
      toast.success('Compliance check started')
      queryClient.invalidateQueries({ queryKey: ['complianceOverview'] })
    },
    onError: (err: Error) => toast.error('Failed to start check: ' + err.message),
  })

  const resultsQuery = useQuery({
    queryKey: ['complianceResultsFiltered', debouncedFilters, page, pageSize],
    queryFn: () =>
      apiClient.getComplianceResults({
        policy_id: debouncedFilters.policyId ? Number(debouncedFilters.policyId) : undefined,
        device_id: debouncedFilters.deviceId ? Number(debouncedFilters.deviceId) : undefined,
        status: debouncedFilters.status || undefined,
        start: debouncedFilters.start?.toISOString(),
        end: debouncedFilters.end?.toISOString(),
        skip: page * pageSize,
        limit: pageSize,
      }),
    keepPreviousData: true,
  })

  const detailMutation = useMutation({
    mutationFn: (id: number) => apiClient.getComplianceResult(id),
    onSuccess: () => setDetailError(''),
    onError: (err: Error) => setDetailError(err.message),
  })

  const policies = overview?.policies ?? []
  const recentResults = overview?.recent_results ?? []
  const latestByPolicy = overview?.latest_by_policy ?? []
  const results = resultsQuery.data ?? recentResults

  if (isLoadingOverview) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Compliance"
          description="Define and run compliance policies against your network devices"
        />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compliance"
        description="Define and run compliance policies against your network devices"
        actions={
          <Button onClick={() => setIsCreateModalOpen(true)} disabled={!canModify} title={!canModify ? 'Viewers cannot create policies' : undefined}>
            <Plus className="mr-2 h-4 w-4" />
            Create Policy
          </Button>
        }
      />

      {overviewError && (
        <Alert variant="destructive">
          <AlertDescription>
            Failed to load compliance overview: {(overviewError as Error).message}
            <Button variant="link" className="px-2" onClick={() => refetchOverview()}>
              Retry
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-muted-foreground" />
              <div>
                <CardTitle>Policies</CardTitle>
                <CardDescription>
                  {policies?.length || 0} compliance{' '}
                  {policies?.length === 1 ? 'policy' : 'policies'} defined
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Last Run</TableHead>
                  <TableHead className="text-right">Pass</TableHead>
                  <TableHead className="text-right">Fail</TableHead>
                  <TableHead className="text-right">Error</TableHead>
                  <TableHead className="w-[120px] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies?.map((policy: CompliancePolicyStats) => (
                  <TableRow key={policy.policy_id}>
                    <TableCell>
                      <div className="font-medium">{policy.name}</div>
                      {policy.description && (
                        <div className="text-xs text-muted-foreground">{policy.description}</div>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {policy.last_run ? formatDateTime(policy.last_run) : '—'}
                    </TableCell>
                    <TableCell className="text-right font-medium text-green-600">
                      {policy.pass_count}
                    </TableCell>
                    <TableCell className="text-right font-medium text-amber-600">
                      {policy.fail_count}
                    </TableCell>
                    <TableCell className="text-right font-medium text-red-600">
                      {policy.error_count}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => runComplianceMutation.mutate(policy.policy_id)}
                        disabled={runComplianceMutation.isPending || !canModify}
                        title={!canModify ? 'Viewers cannot run compliance checks' : undefined}
                      >
                        <Play className="mr-1 h-3 w-3" />
                        Run
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {(!policies || policies.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                      No policies defined yet
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
            {latestByPolicy.length > 0 && (
              <div className="mt-4 space-y-2">
                <Label className="text-xs text-muted-foreground">Latest per policy</Label>
                <div className="flex flex-wrap gap-2">
                  {latestByPolicy.map((item) => (
                    <Badge key={item.id} variant="secondary">
                      {item.policy_name || `Policy #${item.policy_id}`} ·{' '}
                      {item.device_hostname || `Device #${item.device_id}`} · {item.status}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
            {latestByPolicy.length === 0 && (
              <p className="mt-4 text-xs text-muted-foreground">No policy runs yet.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-muted-foreground" />
              <div>
                <CardTitle>Recent Results</CardTitle>
                <CardDescription>Latest compliance check results (filterable)</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="mb-4 flex flex-wrap items-end gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Policy</Label>
                <Select
                  value={filters.policyId}
                  onValueChange={(value) => {
                    setFilters((f) => ({ ...f, policyId: value === 'all' ? '' : value }))
                    setPage(0)
                  }}
                >
                  <SelectTrigger className="w-[140px]">
                    <SelectValue placeholder="All" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    {policies.map((p) => (
                      <SelectItem key={p.policy_id} value={String(p.policy_id)}>
                        {p.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Device ID</Label>
                <Input
                  className="w-[100px]"
                  placeholder="e.g. 12"
                  value={filters.deviceId}
                  onChange={(e) => {
                    setFilters((f) => ({ ...f, deviceId: e.target.value }))
                    setPage(0)
                  }}
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Status</Label>
                <Select
                  value={filters.status || 'any'}
                  onValueChange={(value) => {
                    setFilters((f) => ({ ...f, status: value === 'any' ? '' : value }))
                    setPage(0)
                  }}
                >
                  <SelectTrigger className="w-[100px]">
                    <SelectValue placeholder="Any" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="any">Any</SelectItem>
                    <SelectItem value="pass">Pass</SelectItem>
                    <SelectItem value="fail">Fail</SelectItem>
                    <SelectItem value="error">Error</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <DateTimePicker
                value={filters.start}
                onChange={(date) => {
                  setFilters((f) => ({ ...f, start: date }))
                  setPage(0)
                }}
                placeholder="Start date"
                className="w-[180px]"
              />
              <DateTimePicker
                value={filters.end}
                onChange={(date) => {
                  setFilters((f) => ({ ...f, end: date }))
                  setPage(0)
                }}
                placeholder="End date"
                className="w-[180px]"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setFilters({ policyId: '', deviceId: '', status: '', start: undefined, end: undefined })
                  setPage(0)
                }}
              >
                Reset
              </Button>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>Page size</span>
                <Select
                  value={String(pageSize)}
                  onValueChange={(value) => {
                    setPageSize(Number(value))
                    setPage(0)
                  }}
                >
                  <SelectTrigger className="h-8 w-[70px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {[10, 20, 50].map((n) => (
                      <SelectItem key={n} value={String(n)}>
                        {n}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            {resultsQuery.isFetching && (
              <p className="mb-2 text-xs text-muted-foreground">Updating results…</p>
            )}
            {resultsQuery.error && (
              <Alert variant="destructive" className="mb-3">
                <AlertDescription>
                  Failed to load results: {(resultsQuery.error as Error).message}
                </AlertDescription>
              </Alert>
            )}
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device</TableHead>
                  <TableHead>Policy</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead className="text-right">Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results?.map((res: ComplianceResult) => (
                  <TableRow key={res.id}>
                    <TableCell className="font-medium">
                      {res.device_hostname || `Device #${res.device_id}`}
                    </TableCell>
                    <TableCell>{res.policy_name || `Policy #${res.policy_id}`}</TableCell>
                    <TableCell>
                      <StatusBadge status={res.status} />
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDateTime(res.ts)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setDetailOpen(true)
                          detailMutation.mutate(res.id)
                        }}
                      >
                        View
                      </Button>
                      {res.job_id && (
                        <Button size="sm" variant="link" className="px-1" asChild>
                          <Link to="/jobs">Job #{res.job_id}</Link>
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {(!results || results.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={5} className="h-24 text-center text-muted-foreground">
                      No results yet
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
            <div className="mt-4 flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                Page {page + 1} · Showing {results?.length ?? 0} of {pageSize}
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 0}
                  onClick={() => setPage((p) => Math.max(0, p - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={(results?.length ?? 0) < pageSize}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Compliance Result Details</DialogTitle>
            <DialogDescription>
              {detailMutation.data
                ? `${detailMutation.data.policy_name || 'Policy'} · ${
                    detailMutation.data.device_hostname ||
                    `Device #${detailMutation.data.device_id}`
                  }`
                : 'Loading result details'}
            </DialogDescription>
          </DialogHeader>
          {detailError && (
            <Alert variant="destructive">
              <AlertDescription>{detailError}</AlertDescription>
            </Alert>
          )}
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
              <Badge variant="outline">{detailMutation.data?.status || '...'}</Badge>
              <span>{formatDateTime(detailMutation.data?.ts)}</span>
              <span>Job #{detailMutation.data?.job_id ?? '—'}</span>
              {detailMutation.data?.job_id && (
                <Link to={`/jobs`} className="text-primary underline underline-offset-2">
                  View in Jobs
                </Link>
              )}
            </div>
            <pre className="max-h-80 overflow-auto rounded-md bg-muted p-3 text-xs">
              {detailMutation.isPending && !detailMutation.data
                ? 'Loading...'
                : JSON.stringify(detailMutation.data?.details_json ?? {}, null, 2)}
            </pre>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDetailOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <PolicyBuilderDialog
        open={isCreateModalOpen}
        onOpenChange={setIsCreateModalOpen}
        onSubmit={(data) => createPolicyMutation.mutate(data)}
        isPending={createPolicyMutation.isPending}
        error={createError}
      />
    </div>
  )
}
