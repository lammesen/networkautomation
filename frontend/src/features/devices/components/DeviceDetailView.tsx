import { useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusBadge } from '@/components/ui/status-badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { DiffViewer, ConfigViewer } from '@/components/ui/code-editor'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  ArrowLeft,
  Server,
  Wifi,
  WifiOff,
  Terminal,
  ScrollText,
  Key,
  MapPin,
  Tag,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Activity,
  FileText,
  ShieldCheck,
  History,
} from 'lucide-react'
import { formatDateTime } from '@/lib/formatters'
import { DeviceTerminalDialog } from './DeviceTerminalDialog'
import type { ConfigSnapshot, ComplianceResult, Job } from '@/types'
import { useAuthStore, selectCanModify } from '@/store/authStore'

export function DeviceDetailView() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const deviceId = id ? parseInt(id, 10) : null
  const canModify = useAuthStore(selectCanModify)

  const [activeTab, setActiveTab] = useState('overview')
  const [terminalOpen, setTerminalOpen] = useState(false)

  // Fetch device details
  const {
    data: device,
    isLoading: deviceLoading,
    error: deviceError,
  } = useQuery({
    queryKey: ['device', deviceId],
    queryFn: () => apiClient.getDevice(deviceId!),
    enabled: !!deviceId,
    refetchInterval: 10000,
  })

  // Fetch credentials for display
  const { data: credentials } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => apiClient.getCredentials(),
  })

  // Fetch config snapshots
  const { data: snapshots, isLoading: snapshotsLoading } = useQuery({
    queryKey: ['device-snapshots', deviceId],
    queryFn: () => apiClient.getDeviceSnapshots(deviceId!, 20),
    enabled: !!deviceId && activeTab === 'config',
  })

  // Fetch compliance results for this device
  const { data: complianceResults, isLoading: complianceLoading } = useQuery({
    queryKey: ['compliance-results', { device_id: deviceId }],
    queryFn: () => apiClient.getComplianceResults({ device_id: deviceId!, limit: 50 }),
    enabled: !!deviceId && activeTab === 'compliance',
  })

  // Fetch jobs for this device (server-side filtering)
  const { data: deviceJobs, isLoading: jobsLoading } = useQuery({
    queryKey: ['device-jobs', deviceId],
    queryFn: () => apiClient.getDeviceJobs(deviceId!, { limit: 50 }),
    enabled: !!deviceId && activeTab === 'jobs',
  })

  const credentialName = useMemo(() => {
    if (!credentials || !device) return null
    return credentials.find((c) => c.id === device.credentials_ref)?.name
  }, [credentials, device])

  if (!deviceId) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Invalid device ID</div>
      </div>
    )
  }

  if (deviceLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-10 w-48" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (deviceError || !device) {
    return (
      <div className="space-y-6">
        <Button variant="ghost" onClick={() => navigate('/devices')}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Devices
        </Button>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <p className="text-destructive">Device not found or failed to load</p>
          </div>
        </div>
      </div>
    )
  }

  const reachabilityIcon =
    device.reachability_status === 'reachable' ? (
      <Wifi className="h-5 w-5 text-green-500" />
    ) : device.reachability_status === 'unreachable' ? (
      <WifiOff className="h-5 w-5 text-red-500" />
    ) : (
      <Wifi className="h-5 w-5 text-gray-400" />
    )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/devices')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <PageHeader
          title={
            <div className="flex items-center gap-3">
              <Server className="h-6 w-6" />
              {device.hostname}
              {!device.enabled && (
                <Badge variant="destructive" className="ml-2">
                  Disabled
                </Badge>
              )}
            </div>
          }
          description={`${device.vendor} ${device.platform} • ${device.mgmt_ip}`}
          actions={
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => setTerminalOpen(true)} disabled={!device.enabled || !canModify} title={!canModify ? 'Viewers cannot open terminal' : undefined}>
                <Terminal className="h-4 w-4 mr-2" />
                Terminal
              </Button>
              <Button variant="outline" asChild disabled={!canModify}>
                <Link to={`/commands?device=${device.id}`} className={!canModify ? 'pointer-events-none opacity-50' : ''}>
                  <ScrollText className="h-4 w-4 mr-2" />
                  Run Commands
                </Link>
              </Button>
            </div>
          }
        />
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Reachability</CardTitle>
            {reachabilityIcon}
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold capitalize">
              {device.reachability_status || 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground">
              {device.last_reachability_check
                ? `Last checked ${formatDateTime(device.last_reachability_check)}`
                : 'Never checked'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Location</CardTitle>
            <MapPin className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{device.site || 'Not set'}</div>
            <p className="text-xs text-muted-foreground">{device.role || 'No role assigned'}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Credentials</CardTitle>
            <Key className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{credentialName || 'Unknown'}</div>
            <p className="text-xs text-muted-foreground">Credential set #{device.credentials_ref}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Status</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-semibold">{device.enabled ? 'Enabled' : 'Disabled'}</div>
            <p className="text-xs text-muted-foreground">
              Created {formatDateTime(device.created_at)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview" className="gap-2">
            <FileText className="h-4 w-4" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="config" className="gap-2">
            <ScrollText className="h-4 w-4" />
            Config History
          </TabsTrigger>
          <TabsTrigger value="compliance" className="gap-2">
            <ShieldCheck className="h-4 w-4" />
            Compliance
          </TabsTrigger>
          <TabsTrigger value="jobs" className="gap-2">
            <History className="h-4 w-4" />
            Job History
          </TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-6">
          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Device Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-muted-foreground">Hostname</div>
                    <div className="font-medium">{device.hostname}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Management IP</div>
                    <code className="text-sm bg-muted px-2 py-0.5 rounded">{device.mgmt_ip}</code>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Vendor</div>
                    <div className="font-medium">{device.vendor}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Platform</div>
                    <Badge variant="outline">{device.platform.toUpperCase()}</Badge>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Site</div>
                    <div className="font-medium">{device.site || '-'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-muted-foreground">Role</div>
                    <div className="font-medium">{device.role || '-'}</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Device Facts</CardTitle>
                <CardDescription>Information gathered from the device</CardDescription>
              </CardHeader>
              <CardContent>
                {device.tags && typeof device.tags === 'object' && 'facts' in device.tags ? (
                  <div className="space-y-2">
                    {Object.entries(device.tags.facts as Record<string, string>).map(
                      ([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="text-sm text-muted-foreground capitalize">
                            {key.replace(/_/g, ' ')}
                          </span>
                          <span className="text-sm font-medium">{String(value)}</span>
                        </div>
                      )
                    )}
                  </div>
                ) : (
                  <div className="text-muted-foreground text-sm">
                    No device facts available. Run a config backup job to gather facts.
                  </div>
                )}
              </CardContent>
            </Card>

            {device.tags && Object.keys(device.tags).filter((k) => k !== 'facts').length > 0 && (
              <Card className="md:col-span-2">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Tag className="h-4 w-4" />
                    Tags
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(device.tags)
                      .filter(([key]) => key !== 'facts')
                      .map(([key, value]) => (
                        <Badge key={key} variant="secondary">
                          {key}: {String(value)}
                        </Badge>
                      ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Config History Tab */}
        <TabsContent value="config">
          <ConfigHistoryTab
            deviceId={deviceId}
            snapshots={snapshots || []}
            isLoading={snapshotsLoading}
          />
        </TabsContent>

        {/* Compliance Tab */}
        <TabsContent value="compliance">
          <ComplianceTab results={complianceResults || []} isLoading={complianceLoading} />
        </TabsContent>

        {/* Jobs Tab */}
        <TabsContent value="jobs">
          <JobHistoryTab jobs={deviceJobs || []} isLoading={jobsLoading} />
        </TabsContent>
      </Tabs>

      {/* Terminal Dialog */}
      <DeviceTerminalDialog
        open={terminalOpen}
        device={device}
        onClose={() => setTerminalOpen(false)}
      />
    </div>
  )
}

// Config History Tab Component
function ConfigHistoryTab({
  deviceId,
  snapshots,
  isLoading,
}: {
  deviceId: number
  snapshots: ConfigSnapshot[]
  isLoading: boolean
}) {
  const [fromId, setFromId] = useState<number | null>(null)
  const [toId, setToId] = useState<number | null>(null)
  const [selectedSnapshot, setSelectedSnapshot] = useState<number | null>(null)

  // Auto-select first two snapshots for diff
  useMemo(() => {
    if (snapshots.length >= 2 && !fromId && !toId) {
      setFromId(snapshots[1].id)
      setToId(snapshots[0].id)
    }
  }, [snapshots, fromId, toId])

  // Fetch diff when both selected
  const { data: diffData } = useQuery({
    queryKey: ['config-diff', deviceId, fromId, toId],
    queryFn: () => apiClient.getDeviceConfigDiff(deviceId, fromId!, toId!),
    enabled: !!fromId && !!toId && fromId !== toId,
  })

  // Fetch single snapshot content
  const { data: snapshotContent } = useQuery({
    queryKey: ['snapshot-content', selectedSnapshot],
    queryFn: async () => {
      // Find the snapshot and return its config_text
      const snapshot = snapshots.find((s) => s.id === selectedSnapshot)
      return snapshot?.config_text || 'Config text not available'
    },
    enabled: !!selectedSnapshot,
  })

  const dateFormatter = useMemo(
    () =>
      new Intl.DateTimeFormat('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }),
    []
  )

  if (isLoading) {
    return <Skeleton className="h-96 w-full" />
  }

  if (snapshots.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center h-64">
          <ScrollText className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No configuration snapshots available</p>
          <p className="text-sm text-muted-foreground mt-2">
            Run a config backup job to capture device configurations
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Snapshot List */}
      <Card>
        <CardHeader>
          <CardTitle>Configuration Snapshots</CardTitle>
          <CardDescription>{snapshots.length} snapshots available</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Job</TableHead>
                <TableHead>Hash</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {snapshots.map((snapshot) => (
                <TableRow key={snapshot.id}>
                  <TableCell>{dateFormatter.format(new Date(snapshot.created_at))}</TableCell>
                  <TableCell>
                    <Badge variant="outline">{snapshot.source}</Badge>
                  </TableCell>
                  <TableCell>
                    {snapshot.job_id ? (
                      <Link
                        to={`/jobs?id=${snapshot.job_id}`}
                        className="text-primary hover:underline"
                      >
                        #{snapshot.job_id}
                      </Link>
                    ) : (
                      '-'
                    )}
                  </TableCell>
                  <TableCell>
                    <code className="text-xs">{snapshot.hash.substring(0, 12)}...</code>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        setSelectedSnapshot(selectedSnapshot === snapshot.id ? null : snapshot.id)
                      }
                    >
                      {selectedSnapshot === snapshot.id ? 'Hide' : 'View'}
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Single Snapshot View */}
      {selectedSnapshot && snapshotContent && (
        <Card>
          <CardHeader>
            <CardTitle>Snapshot #{selectedSnapshot}</CardTitle>
          </CardHeader>
          <CardContent>
            <ConfigViewer config={snapshotContent} height={400} />
          </CardContent>
        </Card>
      )}

      {/* Diff View */}
      {snapshots.length >= 2 && (
        <Card>
          <CardHeader>
            <CardTitle>Compare Configurations</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4 items-center">
              <div className="flex-1">
                <span className="text-sm text-muted-foreground">From</span>
                <Select
                  value={fromId?.toString() ?? ''}
                  onValueChange={(val) => setFromId(Number(val))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select snapshot" />
                  </SelectTrigger>
                  <SelectContent>
                    {snapshots.map((s) => (
                      <SelectItem key={s.id} value={s.id.toString()}>
                        {dateFormatter.format(new Date(s.created_at))} ({s.source})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1">
                <span className="text-sm text-muted-foreground">To</span>
                <Select
                  value={toId?.toString() ?? ''}
                  onValueChange={(val) => setToId(Number(val))}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select snapshot" />
                  </SelectTrigger>
                  <SelectContent>
                    {snapshots.map((s) => (
                      <SelectItem key={s.id} value={s.id.toString()}>
                        {dateFormatter.format(new Date(s.created_at))} ({s.source})
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {fromId && toId && fromId === toId && (
              <div className="text-muted-foreground text-center py-8">
                Select different snapshots to compare
              </div>
            )}

            {fromId && toId && fromId !== toId && (
              <DiffViewer diff={diffData?.diff || 'Loading diff...'} height={400} />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// Compliance Tab Component
function ComplianceTab({
  results,
  isLoading,
}: {
  results: ComplianceResult[]
  isLoading: boolean
}) {
  if (isLoading) {
    return <Skeleton className="h-96 w-full" />
  }

  if (results.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center h-64">
          <ShieldCheck className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No compliance checks have been run</p>
          <p className="text-sm text-muted-foreground mt-2">
            Create a compliance policy and run a check to see results
          </p>
        </CardContent>
      </Card>
    )
  }

  // Group by policy for summary
  const byPolicy = results.reduce(
    (acc, r) => {
      const key = r.policy_name || `Policy #${r.policy_id}`
      if (!acc[key]) acc[key] = []
      acc[key].push(r)
      return acc
    },
    {} as Record<string, ComplianceResult[]>
  )

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Passing</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {results.filter((r) => r.status === 'pass').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failing</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {results.filter((r) => r.status === 'fail').length}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Errors</CardTitle>
            <AlertCircle className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">
              {results.filter((r) => r.status === 'error').length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Results by Policy */}
      {Object.entries(byPolicy).map(([policyName, policyResults]) => (
        <Card key={policyName}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4" />
              {policyName}
            </CardTitle>
            <CardDescription>{policyResults.length} check(s)</CardDescription>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Status</TableHead>
                  <TableHead>Checked At</TableHead>
                  <TableHead>Job</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policyResults.slice(0, 10).map((result) => (
                  <TableRow key={result.id}>
                    <TableCell>
                      <StatusBadge status={result.status} />
                    </TableCell>
                    <TableCell>{formatDateTime(result.ts)}</TableCell>
                    <TableCell>
                      <Link to={`/jobs?id=${result.job_id}`} className="text-primary hover:underline">
                        #{result.job_id}
                      </Link>
                    </TableCell>
                    <TableCell className="max-w-md">
                      <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                        {JSON.stringify(result.details_json, null, 2).substring(0, 200)}
                        {JSON.stringify(result.details_json).length > 200 && '...'}
                      </pre>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}

// Job History Tab Component
function JobHistoryTab({ jobs, isLoading }: { jobs: Job[]; isLoading: boolean }) {
  if (isLoading) {
    return <Skeleton className="h-96 w-full" />
  }

  if (jobs.length === 0) {
    return (
      <Card>
        <CardContent className="flex flex-col items-center justify-center h-64">
          <History className="h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-muted-foreground">No jobs have targeted this device</p>
          <p className="text-sm text-muted-foreground mt-2">
            Run commands or automation jobs to see history
          </p>
        </CardContent>
      </Card>
    )
  }

  const formatJobType = (type: string) => {
    return type
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Job History</CardTitle>
        <CardDescription>Jobs that have targeted this device</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Job ID</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Started</TableHead>
              <TableHead>Finished</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.slice(0, 20).map((job) => (
              <TableRow key={job.id}>
                <TableCell>
                  <Link to={`/jobs?id=${job.id}`} className="text-primary hover:underline font-medium">
                    #{job.id}
                  </Link>
                </TableCell>
                <TableCell>{formatJobType(job.type)}</TableCell>
                <TableCell>
                  <StatusBadge status={job.status} />
                </TableCell>
                <TableCell>{formatDateTime(job.started_at)}</TableCell>
                <TableCell>{formatDateTime(job.finished_at || job.completed_at)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {jobs.length > 20 && (
          <div className="text-center text-sm text-muted-foreground mt-4">
            Showing 20 of {jobs.length} jobs
          </div>
        )}
      </CardContent>
    </Card>
  )
}
