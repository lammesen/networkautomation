import { useEffect, useMemo, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { apiClient } from '@/api/client'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'

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
  const [snapshots, setSnapshots] = useState<Snapshot[]>([])
  const [fromId, setFromId] = useState<number | null>(null)
  const [toId, setToId] = useState<number | null>(null)
  const [diff, setDiff] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !deviceId) return
    setError(null)
    setDiff('')
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
      .catch((err: any) => {
        setError(err.response?.data?.detail || 'Failed to load snapshots')
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
      .catch((err: any) => {
        setError(err.response?.data?.detail || 'Failed to load diff')
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
      })),
    [snapshots, dateFormatter]
  )

  return (
    <Dialog open={open} onOpenChange={(val) => !val && onClose()}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle>Configuration History — {hostname || `Device ${deviceId}`}</DialogTitle>
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
            <div className="flex gap-4 items-center">
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
                <Select value={toId?.toString() ?? ''} onValueChange={(val) => setToId(Number(val))}>
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
              Showing unified diff ({fromId} → {toId})
            </div>

            <ScrollArea className="h-[400px] rounded-md border bg-slate-950 text-slate-50 p-4">
              <pre className="text-xs whitespace-pre-wrap">{diff || 'Select snapshots to view diff.'}</pre>
            </ScrollArea>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
