import { useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DEFAULT_COMMAND_SNIPPETS } from '../types'

interface CommandEditorProps {
  commands: string
  cursorPos: number
  suggestions: string[]
  hasPlatform: boolean
  previewMode: 'commands' | 'payload'
  payloadPreview: string
  onCommandsChange: (value: string) => void
  onCursorChange: (pos: number) => void
  onPreviewModeChange: (mode: 'commands' | 'payload') => void
  onKeyDown: (e: React.KeyboardEvent) => void
}

export function CommandEditor({
  commands,
  cursorPos,
  suggestions,
  hasPlatform,
  previewMode,
  payloadPreview,
  onCommandsChange,
  onCursorChange,
  onPreviewModeChange,
  onKeyDown,
}: CommandEditorProps) {
  const getCurrentLine = (text: string, pos: number) => {
    const textBeforeCursor = text.slice(0, pos)
    const lines = textBeforeCursor.split('\n')
    return lines[lines.length - 1]
  }

  const currentLineText = getCurrentLine(commands, cursorPos)

  const firstSuggestion = useMemo(() => {
    if (!hasPlatform || !commands || !currentLineText) return null
    return suggestions.find(
      (s) =>
        s.toLowerCase().startsWith(currentLineText.toLowerCase()) &&
        s.toLowerCase() !== currentLineText.toLowerCase()
    ) ?? null
  }, [hasPlatform, commands, currentLineText, suggestions])

  const recentSnippets = DEFAULT_COMMAND_SNIPPETS.slice(0, 3)
  const lineCount = commands.split('\n').filter((c) => c.trim()).length

  const handleAddSnippet = (snippet: string) => {
    onCommandsChange(commands ? commands + `\n${snippet}` : snippet)
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-2">
        <div className="flex items-center justify-between gap-3 flex-wrap">
          <div>
            <CardTitle>Commands</CardTitle>
            <CardDescription>
              Commands run in parallel on all matching devices. One per line; press Tab to accept
              autocomplete.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <div className="flex flex-wrap gap-2">
              {recentSnippets.map((snippet) => (
                <Badge
                  key={snippet}
                  variant="outline"
                  className="cursor-pointer"
                  onClick={() => handleAddSnippet(snippet)}
                >
                  + {snippet}
                </Badge>
              ))}
            </div>
            <Tabs
              value={previewMode}
              onValueChange={(v) => onPreviewModeChange(v as 'commands' | 'payload')}
            >
              <TabsList>
                <TabsTrigger value="commands">Editor</TabsTrigger>
                <TabsTrigger value="payload">Preview</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>
      </CardHeader>
      <CardContent className="relative">
        {previewMode === 'commands' ? (
          <div className="space-y-2">
            <Textarea
              value={commands}
              onChange={(e) => {
                onCommandsChange(e.target.value)
                onCursorChange(e.target.selectionStart)
              }}
              onSelect={(e) => onCursorChange((e.target as HTMLTextAreaElement).selectionStart)}
              onClick={(e) => onCursorChange((e.target as HTMLTextAreaElement).selectionStart)}
              onKeyDown={onKeyDown}
              placeholder="Enter commands, one per line..."
              rows={8}
              className="font-mono bg-slate-50"
            />
            <div className="flex items-center justify-between text-sm text-muted-foreground">
              {firstSuggestion ? (
                <span>
                  Suggestion: <span className="font-mono font-bold">{firstSuggestion}</span> (Tab)
                </span>
              ) : (
                <span>Autocomplete shows when a platform is selected.</span>
              )}
              <span>{lineCount} lines</span>
            </div>
          </div>
        ) : (
          <div className="rounded-md border bg-slate-950 text-slate-100 p-4 font-mono text-xs whitespace-pre-wrap">
            {payloadPreview}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
