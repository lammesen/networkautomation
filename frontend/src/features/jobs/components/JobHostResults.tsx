import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatusBadge } from '@/components/ui/status-badge'
import { CodeEditor, DiffViewer } from '@/components/ui/code-editor'
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
                  <div key={cmd} className="space-y-1">
                    <div className="text-sm font-medium text-muted-foreground">$ {cmd}</div>
                    <CodeEditor
                      value={typeof output === 'string' ? output : JSON.stringify(output, null, 2)}
                      language="cisco-ios"
                      height={Math.min(200, (typeof output === 'string' ? output.split('\n').length : 10) * 20 + 20)}
                      readOnly
                      showLineNumbers={false}
                    />
                  </div>
                ))}
              </div>
            )}

            {res.diff && (
              <div className="space-y-1">
                <div className="text-sm font-medium text-muted-foreground">Config Diff</div>
                <DiffViewer
                  diff={res.diff}
                  height={Math.min(250, res.diff.split('\n').length * 20 + 20)}
                />
              </div>
            )}

            {res.result && !res.results && (
              <CodeEditor
                value={typeof res.result === 'string' ? res.result : JSON.stringify(res.result, null, 2)}
                language="cisco-ios"
                height={Math.min(200, (typeof res.result === 'string' ? res.result.split('\n').length : 10) * 20 + 20)}
                readOnly
                showLineNumbers={false}
              />
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
