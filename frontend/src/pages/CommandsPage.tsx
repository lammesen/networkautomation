import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { toast } from "sonner"

const SUPPORTED_PLATFORMS = ['ios', 'nxos', 'eos', 'junos']

export default function CommandsPage() {
  const [targets, setTargets] = useState({ site: '', role: '', vendor: '', platform: '' })
  const [commands, setCommands] = useState('')
  const [result, setResult] = useState<any>(null)
  const [cursorPos, setCursorPos] = useState(0)
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [invalidCommands, setInvalidCommands] = useState<string[]>([])
  
  // Fetch suggestions based on selected platform
  const { data: suggestions = [] } = useQuery({
    queryKey: ['commandSuggestions', targets.platform],
    queryFn: () => apiClient.getCommandSuggestions(targets.platform),
    enabled: !!targets.platform,
  })

  const runCommandsMutation = useMutation({
    mutationFn: (data: any) => apiClient.runCommands(data),
    onSuccess: (data) => {
      setResult({ success: true, job_id: data.job_id })
      toast.success(`Job started: #${data.job_id}`)
    },
    onError: (error: any) => {
      setResult({ success: false, error: error.message })
      toast.error(error.message || "Failed to start job")
    },
  })

  const executeRun = () => {
    const commandList = commands.split('\n').filter(cmd => cmd.trim())
    const targetFilters: any = {}
    if (targets.site) targetFilters.site = targets.site
    if (targets.role) targetFilters.role = targets.role
    if (targets.vendor) targetFilters.vendor = targets.vendor
    if (targets.platform) targetFilters.platform = targets.platform
    
    runCommandsMutation.mutate({
      targets: targetFilters,
      commands: commandList,
    })
    setConfirmDialogOpen(false)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const commandList = commands.split('\n').filter(cmd => cmd.trim())
    
    // Validation: Check if commands are in the suggestion list (if platform is selected)
    if (targets.platform && targets.platform !== 'unknown' && suggestions.length > 0) {
      const invalid = commandList.filter(cmd => !suggestions.includes(cmd.trim()))
      if (invalid.length > 0) {
        setInvalidCommands(invalid)
        setConfirmDialogOpen(true)
        return
      }
    }

    executeRun()
  }

  // Autocomplete logic
  const getCurrentLine = (text: string, pos: number) => {
    const textBeforeCursor = text.slice(0, pos)
    const lines = textBeforeCursor.split('\n')
    return lines[lines.length - 1]
  }

  const currentLineText = getCurrentLine(commands, cursorPos)
  
  const firstSuggestion = (targets.platform && commands && currentLineText)
    ? suggestions.find((s: string) => 
        s.toLowerCase().startsWith(currentLineText.toLowerCase()) &&
        s.toLowerCase() !== currentLineText.toLowerCase()
      )
    : null

  const handleKeyDown = (e: React.KeyboardEvent) => {
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
    <div className="space-y-6 max-w-4xl">
      <h1 className="text-3xl font-bold tracking-tight">Run Commands</h1>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Target Selection */}
        <Card>
          <CardHeader>
            <CardTitle>Target Devices</CardTitle>
            <CardDescription>
              Select a platform to enable command autocompletion. Press Tab to accept suggestions.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label htmlFor="site">Site</Label>
                <Input
                  id="site"
                  value={targets.site}
                  onChange={(e) => setTargets({ ...targets, site: e.target.value })}
                  placeholder="e.g., dc1"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Input
                  id="role"
                  value={targets.role}
                  onChange={(e) => setTargets({ ...targets, role: e.target.value })}
                  placeholder="e.g., edge"
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="vendor">Vendor</Label>
                <Input
                  id="vendor"
                  value={targets.vendor}
                  onChange={(e) => setTargets({ ...targets, vendor: e.target.value })}
                  placeholder="e.g., cisco"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="platform">Platform</Label>
                <Select 
                  value={targets.platform} 
                  onValueChange={value => setTargets({ ...targets, platform: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select Platform" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="unknown">Select Platform</SelectItem> {/* Workaround for unselect */}
                    {SUPPORTED_PLATFORMS.map(p => (
                      <SelectItem key={p} value={p}>{p.toUpperCase()}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Commands Input */}
        <Card>
          <CardHeader>
            <CardTitle>Commands</CardTitle>
            <CardDescription>
              Commands will be executed on all matching devices in parallel
            </CardDescription>
          </CardHeader>
          <CardContent className="relative">
             <div className="relative">
                {/* Ghost Text Overlay - simplistic approach for shadcn/tailwind */}
                {/* Note: Precise overlay alignment with Textarea in all browsers is tricky. 
                    For this migration, we'll rely on the user knowing they can press Tab if suggestions appear.
                    Or we can try to preserve the overlay if essential.
                */}
                {/* <div
                  aria-hidden="true"
                  className="absolute inset-0 p-3 border border-transparent font-mono text-sm text-gray-400 pointer-events-none whitespace-pre-wrap overflow-hidden z-0"
                >
                  {commands.slice(0, cursorPos - currentLineText.length)}
                  <span className="text-transparent">{currentLineText}</span>
                  {firstSuggestion ? firstSuggestion.slice(currentLineText.length) : ''}
                </div> */}
                
                <Textarea
                  value={commands}
                  onChange={(e) => {
                    setCommands(e.target.value)
                    setCursorPos(e.target.selectionStart)
                  }}
                  onSelect={(e: any) => setCursorPos(e.target.selectionStart)}
                  onClick={(e: any) => setCursorPos(e.target.selectionStart)}
                  onKeyDown={handleKeyDown}
                  placeholder="Enter commands, one per line..."
                  required
                  rows={8}
                  className="font-mono z-10 relative bg-transparent"
                />
              </div>
              {firstSuggestion && (
                  <div className="mt-2 text-sm text-muted-foreground">
                      Suggestion: <span className="font-mono font-bold">{firstSuggestion}</span> (Press Tab)
                  </div>
              )}
          </CardContent>
        </Card>

        <Button type="submit" disabled={runCommandsMutation.isPending} size="lg">
          {runCommandsMutation.isPending ? 'Submitting...' : 'Run Commands'}
        </Button>
      </form>

      {/* Result */}
      {result && (
        <Alert variant={result.success ? 'default' : 'destructive'} className={result.success ? "bg-green-50 border-green-200 text-green-800" : ""}>
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

      <AlertDialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Unrecognized Commands</AlertDialogTitle>
            <AlertDialogDescription>
              The following commands are not in the standard suggestion list for {targets.platform}:
              <br/><br/>
              <div className="bg-muted p-2 rounded-md font-mono text-sm max-h-[150px] overflow-y-auto">
                {invalidCommands.map((cmd, i) => (
                  <div key={i}>{cmd}</div>
                ))}
              </div>
              <br/>
              Do you want to proceed anyway?
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={executeRun}>
              Proceed
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}