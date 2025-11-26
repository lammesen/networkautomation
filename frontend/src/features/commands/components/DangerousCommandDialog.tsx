import { useState } from 'react'
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { AlertTriangle } from 'lucide-react'

interface DangerousCommandDialogProps {
  open: boolean
  dangerousCommands: string[]
  targetCount?: number
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}

const CONFIRM_TEXT = 'CONFIRM'

export function DangerousCommandDialog({
  open,
  dangerousCommands,
  targetCount,
  onOpenChange,
  onConfirm,
}: DangerousCommandDialogProps) {
  const [confirmInput, setConfirmInput] = useState('')

  const canConfirm = confirmInput === CONFIRM_TEXT

  const handleConfirm = () => {
    if (canConfirm) {
      setConfirmInput('')
      onConfirm()
    }
  }

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) {
      setConfirmInput('')
    }
    onOpenChange(isOpen)
  }

  return (
    <AlertDialog open={open} onOpenChange={handleOpenChange}>
      <AlertDialogContent className="border-destructive">
        <AlertDialogHeader>
          <div className="flex items-center gap-2 text-destructive">
            <AlertTriangle className="h-5 w-5" />
            <AlertDialogTitle className="text-destructive">
              Dangerous Commands Detected
            </AlertDialogTitle>
          </div>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p className="text-destructive font-medium">
                The following commands may cause service disruption or data loss:
              </p>
              <div className="bg-destructive/10 border border-destructive/20 p-3 rounded-md font-mono text-sm max-h-[150px] overflow-y-auto">
                {dangerousCommands.map((cmd, i) => (
                  <div key={i} className="text-destructive">
                    {cmd}
                  </div>
                ))}
              </div>
              {targetCount && targetCount > 1 && (
                <p className="text-destructive font-semibold">
                  This will affect {targetCount} devices!
                </p>
              )}
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  Type <code className="bg-muted px-1.5 py-0.5 rounded font-mono">{CONFIRM_TEXT}</code> to proceed:
                </p>
                <Input
                  value={confirmInput}
                  onChange={(e) => setConfirmInput(e.target.value)}
                  placeholder={CONFIRM_TEXT}
                  className="font-mono"
                  autoFocus
                />
              </div>
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <Button
            variant="destructive"
            onClick={handleConfirm}
            disabled={!canConfirm}
          >
            Execute Dangerous Commands
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
