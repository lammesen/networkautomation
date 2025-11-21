import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useState } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Alert, AlertDescription } from '@/components/ui/alert'

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [selectedJob, setSelectedJob] = useState<any>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  const { data, isLoading, error } = useQuery({
    queryKey: ['jobs', statusFilter, typeFilter],
    queryFn: () => apiClient.getJobs({
      status: statusFilter !== 'all' ? statusFilter : undefined,
      type: typeFilter !== 'all' ? typeFilter : undefined
    }),
    refetchInterval: 1000, // Poll every 5 seconds
  })

  if (isLoading) return <div>Loading jobs...</div>
  if (error) return <div className="text-red-500">Error loading jobs</div>

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
  }

  const parseResults = (json: string) => {
    try {
      return JSON.parse(json)
    } catch {
      return null
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold tracking-tight">Jobs</h1>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <div className="w-[200px]">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="All Statuses" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="queued">Queued</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="success">Success</SelectItem>
                  <SelectItem value="partial">Partial</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="w-[200px]">
              <Select value={typeFilter} onValueChange={setTypeFilter}>
                <SelectTrigger>
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
                <TableHead>Type</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Started</TableHead>
                <TableHead>Finished</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data && data.length > 0 ? (
                data.map((job: any) => (
                  <TableRow key={job.id}>
                    <TableCell className="font-medium">#{job.id}</TableCell>
                    <TableCell>
                      {job.type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                    </TableCell>
                    <TableCell>
                      {getStatusBadge(job.status)}
                    </TableCell>
                    <TableCell>
                      {job.started_at ? new Date(job.started_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      {job.finished_at ? new Date(job.finished_at).toLocaleString() : '-'}
                    </TableCell>
                    <TableCell>
                      <Button variant="outline" size="sm" onClick={() => handleViewJob(job)}>
                        View Output
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">
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
        <DialogContent className="max-w-[95vw] max-h-[95vh]">
          <DialogHeader>
            <DialogTitle>Job #{selectedJob?.id} Details</DialogTitle>
            <DialogDescription>
              Results per device
            </DialogDescription>
          </DialogHeader>

          <ScrollArea className="h-[80vh] w-full rounded-md border p-4">
            {selectedJob && selectedJob.result_summary_json ? (
              <div className="space-y-6">
                {Object.entries(parseResults(selectedJob.result_summary_json) || {}).map(([hostname, res]: [string, any]) => (
                  <div key={hostname} className="space-y-2">
                    <div className="flex items-center gap-2">
                      <h3 className="font-bold text-lg">{hostname}</h3>
                      {getStatusBadge(res.status)}
                    </div>

                    {res.error && (
                      <Alert variant="destructive" className="py-2">
                        <AlertDescription>{res.error}</AlertDescription>
                      </Alert>
                    )}

                    {res.result && typeof res.result === 'object' ? (
                      // Command outputs are usually { 'cmd': 'output' }
                      Object.entries(res.result).map(([cmd, output]: [string, any]) => (
                        <div key={cmd} className="bg-slate-950 text-slate-50 p-4 rounded-md font-mono text-sm whitespace-pre-wrap">
                          <div className="text-slate-400 mb-2">$ {cmd}</div>
                          <pre>{typeof output === 'string' ? output : JSON.stringify(output, null, 2)}</pre>
                        </div>
                      ))
                    ) : res.result ? (
                      // Fallback for simple result
                      <div className="bg-slate-950 text-slate-50 p-4 rounded-md font-mono text-sm whitespace-pre-wrap">
                        <pre>{JSON.stringify(res.result, null, 2)}</pre>
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center text-muted-foreground">
                No results available yet. Job might be queued or running.
              </div>
            )}
          </ScrollArea>
        </DialogContent>
      </Dialog>
    </div>
  )
}
