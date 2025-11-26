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

interface CommandConfirmDialogProps {
  open: boolean
  platform: string
  invalidCommands: string[]
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}

export function CommandConfirmDialog({
  open,
  platform,
  invalidCommands,
  onOpenChange,
  onConfirm,
}: CommandConfirmDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Unrecognized Commands</AlertDialogTitle>
          <AlertDialogDescription>
            The following commands are not in the standard suggestion list for {platform}:
            <br />
            <br />
            <div className="bg-muted p-2 rounded-md font-mono text-sm max-h-[150px] overflow-y-auto">
              {invalidCommands.map((cmd, i) => (
                <div key={i}>{cmd}</div>
              ))}
            </div>
            <br />
            Do you want to proceed anyway?
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>Proceed</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
