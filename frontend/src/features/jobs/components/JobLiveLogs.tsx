import { ScrollArea } from '@/components/ui/scroll-area'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { formatTime } from '@/lib/formatters'
import type { LiveLogEntry } from '../types'

interface JobLiveLogsProps {
  logs: LiveLogEntry[]
  status: string | null
}

export function JobLiveLogs({ logs, status }: JobLiveLogsProps) {
  return (
    <Card className="border-slate-200">
      <CardHeader className="p-4 pb-2">
        <CardTitle className="text-lg">Live Logs</CardTitle>
        <CardDescription className="text-xs">Status: {status || 'waiting'}</CardDescription>
      </CardHeader>
      <CardContent className="p-4 pt-0">
        {logs.length === 0 ? (
          <div className="text-muted-foreground text-sm">Waiting for logs...</div>
        ) : (
          <ScrollArea className="h-[260px] pr-4">
            <div className="space-y-1.5 font-mono text-xs leading-5">
              {logs.map((log, idx) => (
                <div key={idx} className="flex gap-2 text-slate-800">
                  <span className="text-slate-500">{formatTime(log.ts)}</span>
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
  )
}
