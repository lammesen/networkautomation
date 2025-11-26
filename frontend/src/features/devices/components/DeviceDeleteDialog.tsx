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
import { type Device } from '../types'

interface DeviceDeleteDialogProps {
  open: boolean
  device: Device | null
  onConfirm: () => void
  onCancel: () => void
}

export function DeviceDeleteDialog({ open, device, onConfirm, onCancel }: DeviceDeleteDialogProps) {
  return (
    <AlertDialog open={open} onOpenChange={(value) => !value && onCancel()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete device</AlertDialogTitle>
          <AlertDialogDescription>
            This action will disable{' '}
            <span className="font-semibold">{device?.hostname ?? 'this device'}</span>. You can
            re-enable it later from the UI.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel onClick={onCancel}>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm}>Delete</AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}


