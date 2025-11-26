import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { HostCounts, JobPayload } from '../types'

interface JobSummaryCardProps {
  hostCounts: HostCounts | null
  total?: number
  success?: number
  succeeded?: number
  failed?: number
  partial?: number
  running?: number
  payload: JobPayload | null
}

export function JobSummaryCard({
  hostCounts,
  total,
  success,
  succeeded,
  failed,
  partial,
  running,
  payload,
}: JobSummaryCardProps) {
  const commands = payload?.commands ?? []
  const maxChips = 6
  const uniqueCommands = Array.from(new Set(commands))
  const shownCommands = uniqueCommands.slice(0, maxChips)
  const remainingCount = uniqueCommands.length - shownCommands.length

  return (
    <Card className="border-slate-200">
      <CardHeader className="p-4 pb-2">
        <CardTitle className="text-lg">Summary</CardTitle>
        <CardDescription className="text-xs">Quick totals and commands</CardDescription>
      </CardHeader>
      <CardContent className="p-4 pt-1 space-y-3">
        <div className="flex flex-wrap gap-2 text-xs">
          <Badge variant="secondary" className="px-3 py-1 text-xs">
            Total: {hostCounts?.total ?? total ?? '-'}
          </Badge>
          <Badge variant="secondary" className="px-3 py-1 text-xs">
            Success: {hostCounts?.success ?? success ?? succeeded ?? 0}
          </Badge>
          <Badge variant="secondary" className="px-3 py-1 text-xs">
            Failed: {hostCounts?.failed ?? failed ?? 0}
          </Badge>
          <Badge variant="secondary" className="px-3 py-1 text-xs">
            Partial: {hostCounts?.partial ?? partial ?? 0}
          </Badge>
          <Badge variant="secondary" className="px-3 py-1 text-xs">
            Running: {hostCounts?.running ?? running ?? 0}
          </Badge>
        </div>

        {commands.length > 0 ? (
          <div className="flex flex-wrap gap-2 text-xs">
            {shownCommands.map((cmd, idx) => (
              <Badge key={`${cmd}-${idx}`} variant="outline" className="px-3 py-1 text-xs">
                {cmd}
              </Badge>
            ))}
            {remainingCount > 0 && (
              <span className="text-muted-foreground text-xs">+{remainingCount} more</span>
            )}
          </div>
        ) : (
          <div className="text-muted-foreground text-sm">No commands recorded.</div>
        )}
      </CardContent>
    </Card>
  )
}
