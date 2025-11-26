import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { toast } from 'sonner'
import { PageHeader } from '@/components/layout/page-header'
import { TargetFilters } from './TargetFilters'
import { CommandEditor } from './CommandEditor'
import { CommandConfirmDialog } from './CommandConfirmDialog'
import { useCommandSuggestions, useRunCommands } from '../hooks/useCommands'
import type { CommandTargets } from '../types'

interface CommandResult {
  success: boolean
  job_id?: number
  error?: string
}

export function CommandsView() {
  const [targets, setTargets] = useState<CommandTargets>({
    site: '',
    role: '',
    vendor: '',
    platform: '',
  })
  const [commands, setCommands] = useState('')
  const [cursorPos, setCursorPos] = useState(0)
  const [result, setResult] = useState<CommandResult | null>(null)
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [invalidCommands, setInvalidCommands] = useState<string[]>([])
  const [previewMode, setPreviewMode] = useState<'commands' | 'payload'>('commands')

  const hasPlatform = Boolean(targets.platform && targets.platform !== 'unknown')
  const populatedTargets = Object.values(targets).some(Boolean)

  const { data: suggestions = [] } = useCommandSuggestions(targets.platform)
  const runCommandsMutation = useRunCommands()

  const commandLines = useMemo(
    () => commands.split('\n').map((c) => c.trim()).filter(Boolean),
    [commands]
  )

  const canSubmit = commandLines.length > 0 && populatedTargets

  const payloadPreview = useMemo(() => {
    const targetFilters: Record<string, string> = {}
    if (targets.site) targetFilters.site = targets.site
    if (targets.role) targetFilters.role = targets.role
    if (targets.vendor) targetFilters.vendor = targets.vendor
    if (hasPlatform) targetFilters.platform = targets.platform

    return JSON.stringify({ targets: targetFilters, commands: commandLines }, null, 2)
  }, [commands, targets, hasPlatform, commandLines])

  const executeRun = () => {
    const targetFilters: Record<string, string> = {}
    if (targets.site) targetFilters.site = targets.site
    if (targets.role) targetFilters.role = targets.role
    if (targets.vendor) targetFilters.vendor = targets.vendor
    if (targets.platform) targetFilters.platform = targets.platform

    runCommandsMutation.mutate(
      { targets: targetFilters, commands: commandLines },
      {
        onSuccess: (data) => {
          setResult({ success: true, job_id: data.job_id })
          toast.success(`Job started: #${data.job_id}`)
        },
        onError: (error: Error) => {
          setResult({ success: false, error: error.message })
          toast.error(error.message || 'Failed to start job')
        },
      }
    )
    setConfirmDialogOpen(false)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!populatedTargets) {
      toast.error('Add at least one target filter (site/role/vendor/platform) before running commands')
      return
    }

    if (commandLines.length === 0) {
      toast.error('Add at least one command')
      return
    }

    // Validation: Check if commands are in the suggestion list (if platform is selected)
    if (hasPlatform && suggestions.length > 0) {
      const invalid = commandLines.filter((cmd) => !suggestions.includes(cmd.trim()))
      if (invalid.length > 0) {
        setInvalidCommands(invalid)
        setConfirmDialogOpen(true)
        return
      }
    }

    executeRun()
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    const getCurrentLine = (text: string, pos: number) => {
      const textBeforeCursor = text.slice(0, pos)
      const lines = textBeforeCursor.split('\n')
      return lines[lines.length - 1]
    }

    const currentLineText = getCurrentLine(commands, cursorPos)
    const firstSuggestion =
      targets.platform && commands && currentLineText
        ? suggestions.find(
            (s: string) =>
              s.toLowerCase().startsWith(currentLineText.toLowerCase()) &&
              s.toLowerCase() !== currentLineText.toLowerCase()
          )
        : null

    if (e.key === 'Tab' && firstSuggestion) {
      e.preventDefault()
      const textBeforeCursor = commands.slice(0, cursorPos)
      const textAfterCursor = commands.slice(cursorPos)
      const lines = textBeforeCursor.split('\n')
      const currentLineLength = lines[lines.length - 1].length

      // Replace current partial word with full suggestion
      const newTextBefore = textBeforeCursor.slice(0, -currentLineLength) + firstSuggestion
      setCommands(newTextBefore + textAfterCursor)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <PageHeader
        title="Run Commands"
        description="Execute CLI commands on targeted network devices"
      />

      <form onSubmit={handleSubmit} className="space-y-6">
        <TargetFilters targets={targets} onChange={setTargets} />

        <CommandEditor
          commands={commands}
          cursorPos={cursorPos}
          suggestions={suggestions}
          hasPlatform={hasPlatform}
          previewMode={previewMode}
          payloadPreview={payloadPreview}
          onCommandsChange={setCommands}
          onCursorChange={setCursorPos}
          onPreviewModeChange={setPreviewMode}
          onKeyDown={handleKeyDown}
        />

        <div className="flex items-center gap-3">
          <Button type="submit" disabled={runCommandsMutation.isPending || !canSubmit} size="lg">
            {runCommandsMutation.isPending ? 'Submitting...' : 'Run Commands'}
          </Button>
          {!populatedTargets && (
            <span className="text-sm text-muted-foreground">
              Tip: add site/role/platform filters to scope blast radius.
            </span>
          )}
        </div>
      </form>

      {result && (
        <Alert
          variant={result.success ? 'default' : 'destructive'}
          className={result.success ? 'bg-green-50 border-green-200 text-green-800' : ''}
        >
          <AlertTitle>{result.success ? 'Job Created Successfully' : 'Error'}</AlertTitle>
          <AlertDescription>
            {result.success ? (
              <>
                <p>Job ID: {result.job_id}</p>
                <p className="text-sm mt-1 opacity-90">Go to the Jobs page to monitor progress</p>
              </>
            ) : (
              result.error
            )}
          </AlertDescription>
        </Alert>
      )}

      <CommandConfirmDialog
        open={confirmDialogOpen}
        platform={targets.platform}
        invalidCommands={invalidCommands}
        onOpenChange={setConfirmDialogOpen}
        onConfirm={executeRun}
      />
    </div>
  )
}
