import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useEffect, useMemo, useRef, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useAuthStore } from '@/store/authStore'
import { Input } from '@/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { MoreHorizontal, RotateCcw, ScrollText } from 'lucide-react'

export default function JobsPage() {
  const user = useAuthStore((s) => s.user)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [scope, setScope] = useState<'all' | 'mine'>(user?.role === 'admin' ? 'all' : 'mine')
  const [textFilter, setTextFilter] = useState('')
  const [selectedJob, setSelectedJob] = useState<any>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [liveLogs, setLiveLogs] = useState<{ ts: string; level: string; message: string; host?: string }[]>([])
  const [liveStatus, setLiveStatus] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const token = useAuthStore((s) => s.token)

  // Custom badge colors using Tailwind classes since shadcn Badge variants are limited
  const getStatusBadge = (status: string) => {
    let classes = ""
    switch (status) {
      case 'success':
        classes = "bg-green-100 text-green-800 hover:bg-green-100 border-green-200"
        break
      case 'running':
        classes = "bg-blue-100 text-blue-800 hover:bg-blue-100 border-blue-200"
        break
      case 'scheduled':
        classes = "bg-indigo-100 text-indigo-800 hover:bg-indigo-100 border-indigo-200"
        break
      case 'failed':
        classes = "bg-red-100 text-red-800 hover:bg-red-100 border-red-200"
        break
      case 'partial':
        classes = "bg-yellow-100 text-yellow-800 hover:bg-yellow-100 border-yellow-200"
        break
      default:
        classes = "bg-gray-100 text-gray-800 hover:bg-gray-100 border-gray-200"
    }

    return (
      <Badge variant="outline" className={classes}>
        {status}
      </Badge>
    )
  }

  const handleViewJob = (job: any) => {
    setSelectedJob(job)
    setIsModalOpen(true)
    setLiveLogs([])
    setLiveStatus(job.status)
  }

  const normalizeJob = (job: any) => ({
    ...job,
    customer_id: job.customer_id ?? job.customer ?? null,
    user_id: job.user_id ?? job.user ?? null,
    started_at: job.started_at ?? job.requested_at ?? null,
    finished_at: job.finished_at ?? job.completed_at ?? null,
  })

  const parseResults = (data: any) => {
    if (!data) return null
    if (typeof data === 'object') return data
    if (typeof data === 'string') {
      try {
        return JSON.parse(data)
      } catch {
        return null
      }
    }
    return null
  }

  const isAdmin = user?.role === 'admin'

  const { data, isLoading, error } = useQuery({
    queryKey: ['jobs', statusFilter, typeFilter, scope],
    queryFn: async () => {
      const params = {
        status: statusFilter !== 'all' ? statusFilter : undefined,
        type: typeFilter !== 'all' ? typeFilter : undefined,
      }

      if (isAdmin && scope === 'all') {
        try {
          return await apiClient.getAdminJobs({ ...params, limit: 200 })
        } catch (err: any) {
          // Some deployments may disable the admin endpoint; gracefully fall back to user-scoped jobs.
          if (err?.response?.status === 422 || err?.response?.status === 404) {
            return apiClient.getJobs(params)
          }
          throw err
        }
      }
      return apiClient.getJobs(params)
    },
    refetchInterval: 1000,
  })

  const wsBase = useMemo(() => {
    const api = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    return api.replace(/^http/, 'ws')
  }, [])

  useEffect(() => {
    if (!isModalOpen || !selectedJob) return
    const url = `${wsBase}/ws/jobs/${selectedJob.id}?token=${encodeURIComponent(token || '')}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'status') {
        setLiveStatus(msg.status)
      } else if (msg.type === 'log') {
        setLiveLogs((prev) => [...prev, { ts: msg.ts, level: msg.level, message: msg.message, host: msg.host }])
      } else if (msg.type === 'complete') {
        setLiveStatus(msg.status)
      }
    }

    ws.onerror = () => {
      setLiveLogs((prev) => [...prev, { ts: new Date().toISOString(), level: 'ERROR', message: 'WebSocket error' }])
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [isModalOpen, selectedJob, wsBase, token])

  const orderedLogs = useMemo(
    () =>
      [...liveLogs].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime()),
    [liveLogs]
  )

  const summary = useMemo(() => parseResults(selectedJob?.result_summary_json), [selectedJob])
  const hostResults = summary?.results || summary?.diffs

  const hostCounts = useMemo(() => {
    if (!hostResults) return null
    const counts = { success: 0, failed: 0, partial: 0, queued: 0, running: 0, total: 0 }
    Object.values(hostResults).forEach((res: any) => {
      const status = res.status || ''
      if (status === 'success') counts.success += 1
      else if (status === 'failed') counts.failed += 1
      else if (status === 'partial') counts.partial += 1
      else if (status === 'queued') counts.queued += 1
      else if (status === 'running') counts.running += 1
      counts.total += 1
    })
    return counts
  }, [hostResults])

  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }),
    []
  )

  const timeFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
      }),
    []
  )

  const filteredJobs = useMemo(() => {
    if (!data) return []
    const query = textFilter.trim().toLowerCase()
    if (!query) return data
    return data.filter((job: any) => {
      const normalized = normalizeJob(job)
      return (
        `#${normalized.id}`.includes(query) ||
        normalized.type?.toLowerCase().includes(query) ||
        (normalized.status?.toLowerCase() || '').includes(query)
      )
    })
  }, [data, textFilter])

  if (isLoading) return <div>Loading jobs...</div>
  if (error) return <div className="text-red-500">Error loading jobs</div>

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Jobs</h1>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap items-center gap-3">
            <Input
              placeholder="Search by ID, type, or status"
              className="w-full sm:w-[260px]"
              value={textFilter}
              onChange={(e) => setTextFilter(e.target.value)}
            />

            <div className="flex gap-2 flex-wrap">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
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

              <Select value={typeFilter} onValueChange={setTypeFilter}>
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
                <Select value={scope} onValueChange={(v: 'all' | 'mine') => setScope(v)}>
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
              Showing {filteredJobs.length} {filteredJobs.length === 1 ? 'job' : 'jobs'}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Jobs Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>ID</TableHead>
                {isAdmin && scope === 'all' && <TableHead>Customer</TableHead>}
                {isAdmin && scope === 'all' && <TableHead>User</TableHead>}
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Finished</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredJobs && filteredJobs.length > 0 ? (
                filteredJobs.map((job: any) => {
                  const normalized = normalizeJob(job)
                  const jobAgeMs = normalized.started_at
                    ? Date.now() - new Date(normalized.started_at).getTime()
                    : 0
                  const twelveHoursMs = 12 * 60 * 60 * 1000
                  const withinRetryWindow = jobAgeMs <= twelveHoursMs || jobAgeMs === 0
                  const canRetry =
                    withinRetryWindow && ['failed', 'partial', 'queued', 'scheduled'].includes(normalized.status)
                  const actions = [
                    {
                      label: 'View output',
                      onSelect: () => handleViewJob(normalized),
                    },
                    canRetry
                      ? {
                          label: 'Retry job',
                          destructive: false,
                          onSelect: () =>
                            apiClient
                              .retryJob(normalized.id)
                              .then((resp) => {
                                setLiveLogs([])
                                setLiveStatus('queued')
                                setSelectedJob({ ...normalized, id: resp.job_id, status: 'queued' })
                                setIsModalOpen(true)
                              })
                              .catch((err) => console.error(err)),
                        }
                      : null,
                  ].filter(Boolean) as { label: string; onSelect: () => void; destructive?: boolean }[]

                  return (
                    <TableRow key={normalized.id}>
                      <TableCell className="font-medium">#{normalized.id}</TableCell>
                      {isAdmin && scope === 'all' && <TableCell>{normalized.customer_id ?? '-'}</TableCell>}
                      {isAdmin && scope === 'all' && <TableCell>{normalized.user_id ?? '-'}</TableCell>}
                      <TableCell>
                        {normalized.type
                          .replace(/_/g, ' ')
                          .replace(/\b\w/g, (l: string) => l.toUpperCase())}
                      </TableCell>
                      <TableCell>{getStatusBadge(normalized.status)}</TableCell>
                      <TableCell>
                        {normalized.started_at ? dateFormatter.format(new Date(normalized.started_at)) : '-'}
                      </TableCell>
                      <TableCell>
                        {normalized.finished_at ? dateFormatter.format(new Date(normalized.finished_at)) : '-'}
                      </TableCell>
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
                            <DropdownMenuItem onSelect={actions[0].onSelect}>
                              <ScrollText className="h-4 w-4 mr-2" />
                              View output
                            </DropdownMenuItem>
                            {canRetry && (
                              <>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem onSelect={actions[1]?.onSelect}>
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
                    colSpan={isAdmin && scope === 'all' ? 8 : 6}
                    className="text-center h-24 text-muted-foreground"
                  >
                    No jobs found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Job Details Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-[95vw] max-h-[95vh]" aria-describedby="job-details-description">
          <DialogHeader>
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div>
                <DialogTitle>Job #{selectedJob?.id}</DialogTitle>
                <DialogDescription id="job-details-description">
                  Results per device and live logs
                </DialogDescription>
              </div>
              {selectedJob?.status && getStatusBadge(selectedJob.status)}
            </div>
          </DialogHeader>

          <ScrollArea className="h-[80vh] w-full rounded-md border p-4">
            <div className="grid gap-4 lg:grid-cols-2">
              <Card className="border-slate-200">
                <CardHeader className="p-4 pb-2">
                  <CardTitle className="text-lg">Live Logs</CardTitle>
                  <CardDescription className="text-xs">Status: {liveStatus || 'waiting'}</CardDescription>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  {orderedLogs.length === 0 ? (
                    <div className="text-muted-foreground text-sm">Waiting for logs...</div>
                  ) : (
                    <ScrollArea className="h-[260px] pr-4">
                      <div className="space-y-1.5 font-mono text-xs leading-5">
                        {orderedLogs.map((log, idx) => (
                          <div key={idx} className="flex gap-2 text-slate-800">
                            <span className="text-slate-500">{timeFormatter.format(new Date(log.ts))}</span>
                            <span className="uppercase text-slate-600">{log.level}</span>
                            {log.host && <span className="text-slate-600">[{log.host}]</span>}
                            <span className="text-slate-900">{log.message}</span>
                          </div>
                        ))}
                      </div>
                    </ScrollArea>
                  )}
                </CardContent>
              </Card>

              <Card className="border-slate-200">
                <CardHeader className="p-4 pb-2">
                  <CardTitle className="text-lg">Summary</CardTitle>
                  <CardDescription className="text-xs">Quick totals and commands</CardDescription>
                </CardHeader>
                <CardContent className="p-4 pt-1 space-y-3">
                  <div className="flex flex-wrap gap-2 text-xs">
                    <Badge variant="secondary" className="px-3 py-1 text-xs">
                      Total: {hostCounts?.total ?? summary?.total ?? '-'}
                    </Badge>
                    <Badge variant="secondary" className="px-3 py-1 text-xs">
                      Success: {hostCounts?.success ?? summary?.success ?? summary?.succeeded ?? 0}
                    </Badge>
                    <Badge variant="secondary" className="px-3 py-1 text-xs">
                      Failed: {hostCounts?.failed ?? summary?.failed ?? 0}
                    </Badge>
                    <Badge variant="secondary" className="px-3 py-1 text-xs">
                      Partial: {hostCounts?.partial ?? summary?.partial ?? 0}
                    </Badge>
                    <Badge variant="secondary" className="px-3 py-1 text-xs">
                      Running: {hostCounts?.running ?? summary?.running ?? 0}
                    </Badge>
                  </div>

                  {selectedJob?.payload_json?.commands?.length ? (
                    (() => {
                      const uniqueCommands = Array.from(new Set(selectedJob.payload_json.commands as string[]))
                      const maxChips = 6
                      const shown = uniqueCommands.slice(0, maxChips)
                      const remaining = uniqueCommands.length - shown.length
                      return (
                        <div className="flex flex-wrap gap-2 text-xs">
                          {shown.map((cmd: string, idx: number) => (
                            <Badge key={`${cmd}-${idx}`} variant="outline" className="px-3 py-1 text-xs">
                              {cmd}
                            </Badge>
                          ))}
                          {remaining > 0 && (
                            <span className="text-muted-foreground text-xs">+{remaining} more</span>
                          )}
                        </div>
                      )
                    })()
                  ) : (
                    <div className="text-muted-foreground text-sm">No commands recorded.</div>
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="mt-4 space-y-3">
              {hostResults && Object.keys(hostResults).length > 0 ? (
                <div className="grid gap-4 lg:grid-cols-2">
                  {Object.entries(hostResults).map(([hostname, res]: [string, any]) => (
                    <Card key={hostname} className="border-slate-200">
                      <CardHeader className="p-4 pb-2 flex flex-row items-center gap-3">
                        <CardTitle className="text-lg leading-tight">{hostname}</CardTitle>
                        {res.status ? getStatusBadge(res.status) : null}
                      </CardHeader>
                      <CardContent className="p-4 pt-1 space-y-3">
                        {res.error && (
                          <Alert variant="destructive" className="py-2">
                            <AlertDescription>{res.error}</AlertDescription>
                          </Alert>
                        )}

                        {res.results && typeof res.results === 'object' && Object.keys(res.results).length > 0 && (
                          <div className="space-y-3">
                            {Object.entries(res.results).map(([cmd, output]: [string, any]) => (
                              <Card key={cmd} className="bg-slate-900 text-slate-100 border-slate-700">
                                <CardHeader className="p-3 pb-0">
                                  <CardTitle className="text-sm text-slate-200">$ {cmd}</CardTitle>
                                </CardHeader>
                                <CardContent className="p-3 pt-2">
                                  <pre className="font-mono text-xs whitespace-pre-wrap leading-5">{typeof output === 'string' ? output : JSON.stringify(output, null, 2)}</pre>
                                </CardContent>
                              </Card>
                            ))}
                          </div>
                        )}

                        {res.diff && (
                          <Card className="bg-slate-900 text-slate-100 border-slate-700">
                            <CardContent className="p-3">
                              <pre className="font-mono text-xs whitespace-pre-wrap leading-5">{res.diff}</pre>
                            </CardContent>
                          </Card>
                        )}

                        {res.result && !res.results && (
                          <Card className="bg-slate-900 text-slate-100 border-slate-700">
                            <CardContent className="p-3">
                              <pre className="font-mono text-xs whitespace-pre-wrap leading-5">{typeof res.result === 'string' ? res.result : JSON.stringify(res.result, null, 2)}</pre>
                            </CardContent>
                          </Card>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-muted-foreground text-sm">No per-device results captured.</div>
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  )
}
