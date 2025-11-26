import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { apiClient } from '@/api/client'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { DiffViewer } from '@/components/ui/code-editor'
import { toast } from 'sonner'
import { RotateCcw, AlertTriangle, Loader2 } from 'lucide-react'

interface Snapshot {
  id: number
  created_at: string
  source: string
  hash: string
  job_id?: number
}

interface Props {
  deviceId: number | null
  hostname?: string
  open: boolean
  onClose: () => void
}

export function ConfigHistoryDialog({ deviceId, hostname, open, onClose }: Props) {
  const navigate = useNavigate()
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [fromId, setFromId] = useState<number | null>(null)
  const [toId, setToId] = useState<number | null>(null)
  const [diff, setDiff] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Rollback state
  const [selectedRollbackId, setSelectedRollbackId] = useState<number | null>(null)
  const [rollbackConfirmOpen, setRollbackConfirmOpen] = useState(false)
  const [rollbackPreviewJobId, setRollbackPreviewJobId] = useState<number | null>(null)
  const [rollbackPreviewDiff, setRollbackPreviewDiff] = useState<string | null>(null)
  const [rollbackCommitConfirmOpen, setRollbackCommitConfirmOpen] = useState(false)
  const [rollbackLoading, setRollbackLoading] = useState(false)

  useEffect(() => {
    if (!open || !deviceId) return
    setError(null)
    setDiff('')
    setRollbackPreviewDiff(null)
    setRollbackPreviewJobId(null)
    setLoading(true)
    apiClient
      .getDeviceSnapshots(deviceId, 50)
      .then((data) => {
        setSnapshots(data)
        if (data.length >= 2) {
          setFromId(data[1].id)
          setToId(data[0].id)
        } else if (data.length === 1) {
          setFromId(data[0].id)
          setToId(data[0].id)
        }
      })
      .catch((err: Error) => {
        setError(err.message || 'Failed to load snapshots')
      })
      .finally(() => setLoading(false))
  }, [open, deviceId])

  useEffect(() => {
    if (!deviceId || !fromId || !toId) return
    if (fromId === toId) {
      setDiff('No change (same snapshot selected).')
      return
    }
    setError(null)
    apiClient
      .getDeviceConfigDiff(deviceId, fromId, toId)
      .then((resp) => setDiff(resp.diff || 'No changes'))
      .catch((err: Error) => {
        setError(err.message || 'Failed to load diff')
      })
  }, [deviceId, fromId, toId])

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

  const snapshotOptions = useMemo(
    () =>
      snapshots.map((s) => ({
        value: s.id.toString(),
        label: `${dateFormatter.format(new Date(s.created_at))} (${s.source})`,
        snapshot: s,
      })),
    [snapshots, dateFormatter]
  )

  const selectedSnapshot = useMemo(
    () => snapshots.find((s) => s.id === selectedRollbackId),
    [snapshots, selectedRollbackId]
  )

  const handleRollbackClick = (snapshotId: number) => {
    setSelectedRollbackId(snapshotId)
    setRollbackConfirmOpen(true)
  }

  const handleRollbackPreview = async () => {
    if (!selectedRollbackId) return

    setRollbackConfirmOpen(false)
    setRollbackLoading(true)
    setError(null)

    try {
      const result = await apiClient.rollbackPreview(selectedRollbackId)
      setRollbackPreviewJobId(result.job_id)
      toast.success(`Rollback preview job started: #${result.job_id}`)

      // Poll for job completion
      const pollForResult = async () => {
        let attempts = 0
        const maxAttempts = 60 // 60 seconds timeout

        while (attempts < maxAttempts) {
          await new Promise((resolve) => setTimeout(resolve, 1000))
          attempts++

          try {
            const job = await apiClient.getJob(result.job_id)

            if (job.status === 'success') {
              const summary = job.result_summary_json as {
                diff?: string
                has_changes?: boolean
              } | null
              setRollbackPreviewDiff(summary?.diff || 'No changes detected')
              setRollbackLoading(false)
              return
            } else if (job.status === 'failed') {
              setError(`Rollback preview failed: ${job.result_summary_json || 'Unknown error'}`)
              setRollbackLoading(false)
              return
            }
            // Still running, continue polling
          } catch {
            // Ignore polling errors, continue
          }
        }

        setError('Rollback preview timed out')
        setRollbackLoading(false)
      }

      pollForResult()
    } catch (err: unknown) {
      const error = err as Error
      setError(error.message || 'Failed to start rollback preview')
      setRollbackLoading(false)
    }
  }

  const handleRollbackCommit = async () => {
    if (!rollbackPreviewJobId) return

    setRollbackCommitConfirmOpen(false)
    setRollbackLoading(true)

    try {
      const result = await apiClient.rollbackCommit(rollbackPreviewJobId)
      toast.success(`Rollback committed! Job #${result.job_id} started.`)

      // Reset state and close
      setRollbackPreviewDiff(null)
      setRollbackPreviewJobId(null)
      setSelectedRollbackId(null)
      setRollbackLoading(false)

      // Navigate to jobs page to track progress
      onClose()
      navigate(`/jobs?highlight=${result.job_id}`)
    } catch (err: unknown) {
      const error = err as Error
      setError(error.message || 'Failed to commit rollback')
      setRollbackLoading(false)
    }
  }

  const handleCancelRollback = () => {
    setRollbackPreviewDiff(null)
    setRollbackPreviewJobId(null)
    setSelectedRollbackId(null)
  }

  return (
    <>
      <Dialog open={open} onOpenChange={(val) => !val && onClose()}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Configuration History - {hostname || `Device ${deviceId}`}</DialogTitle>
            <DialogDescription>
              View configuration snapshots and rollback to previous versions
            </DialogDescription>
          </DialogHeader>

          {loading && <div>Loading snapshots...</div>}
          {error && (
            <Alert variant="destructive" className="mb-3">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {!loading && snapshots.length === 0 && (
            <div className="text-muted-foreground">No configuration snapshots available.</div>
          )}

          {snapshots.length > 0 && (
            <div className="space-y-4">
              {/* Rollback Preview Section */}
              {rollbackPreviewDiff && (
                <Alert className="border-amber-500 bg-amber-50 dark:bg-amber-950/20">
                  <AlertTriangle className="h-4 w-4 text-amber-600" />
                  <AlertDescription className="space-y-3">
                    <div className="font-medium text-amber-800 dark:text-amber-200">
                      Rollback Preview Ready
                    </div>
                    <div className="text-sm text-amber-700 dark:text-amber-300">
                      Review the changes below. Click &quot;Commit Rollback&quot; to apply these
                      changes to the device.
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => setRollbackCommitConfirmOpen(true)}
                        disabled={rollbackLoading}
                      >
                        Commit Rollback
                      </Button>
                      <Button variant="outline" size="sm" onClick={handleCancelRollback}>
                        Cancel
                      </Button>
                    </div>
                  </AlertDescription>
                </Alert>
              )}

              {rollbackLoading && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Processing rollback preview...</span>
                </div>
              )}

              {/* Show rollback preview diff if available */}
              {rollbackPreviewDiff && (
                <div className="space-y-2">
                  <div className="text-sm font-medium">Rollback Preview Diff</div>
                  <DiffViewer diff={rollbackPreviewDiff} height={300} />
                </div>
              )}

              {/* Regular diff comparison */}
              {!rollbackPreviewDiff && (
                <>
                  <div className="flex gap-4 items-end">
                    <div className="flex-1">
                      <span className="text-sm text-muted-foreground">From snapshot</span>
                      <Select
                        value={fromId?.toString() ?? ''}
                        onValueChange={(val) => setFromId(Number(val))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select snapshot" />
                        </SelectTrigger>
                        <SelectContent>
                          {snapshotOptions.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex-1">
                      <span className="text-sm text-muted-foreground">To snapshot</span>
                      <Select
                        value={toId?.toString() ?? ''}
                        onValueChange={(val) => setToId(Number(val))}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select snapshot" />
                        </SelectTrigger>
                        <SelectContent>
                          {snapshotOptions.map((opt) => (
                            <SelectItem key={opt.value} value={opt.value}>
                              {opt.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <Button
                      variant="outline"
                      onClick={() => {
                        setFromId(null)
                        setToId(null)
                        setDiff('')
                      }}
                    >
                      Clear
                    </Button>
                  </div>

                  <div className="text-sm text-muted-foreground">
                    Showing unified diff ({fromId} -&gt; {toId})
                  </div>

                  <DiffViewer diff={diff || 'Select snapshots to view diff.'} height={300} />

                  {/* Snapshot list with rollback buttons */}
                  <div className="border-t pt-4 mt-4">
                    <div className="text-sm font-medium mb-2">Available Snapshots</div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {snapshots.map((snapshot, index) => (
                        <div
                          key={snapshot.id}
                          className="flex items-center justify-between p-2 rounded border hover:bg-muted/50"
                        >
                          <div className="flex-1">
                            <div className="text-sm font-medium">
                              {dateFormatter.format(new Date(snapshot.created_at))}
                            </div>
                            <div className="text-xs text-muted-foreground">
                              Source: {snapshot.source} | Hash: {snapshot.hash.slice(0, 8)}...
                            </div>
                          </div>
                          {index > 0 && ( // Can't rollback to current/latest
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleRollbackClick(snapshot.id)}
                              disabled={rollbackLoading}
                              className="ml-2"
                            >
                              <RotateCcw className="h-3 w-3 mr-1" />
                              Rollback
                            </Button>
                          )}
                          {index === 0 && (
                            <span className="text-xs text-muted-foreground px-2">(Latest)</span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Initial rollback confirmation */}
      <AlertDialog open={rollbackConfirmOpen} onOpenChange={setRollbackConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Preview Rollback?</AlertDialogTitle>
            <AlertDialogDescription>
              This will generate a preview of rolling back to the snapshot from{' '}
              {selectedSnapshot
                ? dateFormatter.format(new Date(selectedSnapshot.created_at))
                : 'the selected time'}
              .
              <br />
              <br />
              No changes will be made to the device until you confirm the commit.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleRollbackPreview}>Preview Rollback</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Final commit confirmation */}
      <AlertDialog open={rollbackCommitConfirmOpen} onOpenChange={setRollbackCommitConfirmOpen}>
        <AlertDialogContent className="border-destructive">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-destructive flex items-center gap-2">
              <AlertTriangle className="h-5 w-5" />
              Confirm Rollback Commit
            </AlertDialogTitle>
            <AlertDialogDescription>
              <strong>This action will modify the device configuration.</strong>
              <br />
              <br />
              The current configuration will be backed up before applying the rollback. Are you sure
              you want to proceed?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRollbackCommit}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Commit Rollback
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
