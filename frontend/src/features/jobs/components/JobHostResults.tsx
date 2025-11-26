import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatusBadge } from '@/components/ui/status-badge'
import type { JobHostResult } from '../types'

interface JobHostResultsProps {
  hostResults: Record<string, JobHostResult>
}

export function JobHostResults({ hostResults }: JobHostResultsProps) {
  const entries = Object.entries(hostResults)

  if (entries.length === 0) {
    return (
      <div className="text-muted-foreground text-sm">No per-device results captured.</div>
    )
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {entries.map(([hostname, res]) => (
        <Card key={hostname} className="border-slate-200">
          <CardHeader className="p-4 pb-2 flex flex-row items-center gap-3">
            <CardTitle className="text-lg leading-tight">{hostname}</CardTitle>
            {res.status && <StatusBadge status={res.status} />}
          </CardHeader>
          <CardContent className="p-4 pt-1 space-y-3">
            {res.error && (
              <Alert variant="destructive" className="py-2">
                <AlertDescription>{res.error}</AlertDescription>
              </Alert>
            )}

            {res.results && typeof res.results === 'object' && Object.keys(res.results).length > 0 && (
              <div className="space-y-3">
                {Object.entries(res.results).map(([cmd, output]) => (
                  <Card key={cmd} className="bg-slate-900 text-slate-100 border-slate-700">
                    <CardHeader className="p-3 pb-0">
                      <CardTitle className="text-sm text-slate-200">$ {cmd}</CardTitle>
                    </CardHeader>
                    <CardContent className="p-3 pt-2">
                      <pre className="font-mono text-xs whitespace-pre-wrap leading-5">
                        {typeof output === 'string' ? output : JSON.stringify(output, null, 2)}
                      </pre>
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
                  <pre className="font-mono text-xs whitespace-pre-wrap leading-5">
                    {typeof res.result === 'string' ? res.result : JSON.stringify(res.result, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
