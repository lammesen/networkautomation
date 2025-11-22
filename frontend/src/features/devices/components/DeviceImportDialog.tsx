import { FormEvent } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

export interface DeviceImportSummary {
  created: number
  skipped: number
  failed: number
  errors: string[]
}

interface DeviceImportDialogProps {
  open: boolean
  error?: string
  isLoading: boolean
  importResult: DeviceImportSummary | null
  onClose: () => void
  onFileChange: (file: File | null) => void
  onSubmit: () => void
}

export function DeviceImportDialog({
  open,
  error,
  isLoading,
  importResult,
  onClose,
  onFileChange,
  onSubmit,
}: DeviceImportDialogProps) {
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit()
  }

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import Devices from CSV</DialogTitle>
          <DialogDescription>Upload a CSV file to bulk import devices.</DialogDescription>
        </DialogHeader>

        {!importResult ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <div className="text-sm text-muted-foreground bg-muted p-2 rounded-md">
                CSV must contain headers:
                <br />
                <code className="text-xs">
                  hostname, mgmt_ip, vendor, platform, credential_name
                </code>
                <br />
                Optional: <code className="text-xs">role, site</code>
              </div>
              <Input
                type="file"
                accept=".csv"
                onChange={(e) => onFileChange(e.target.files?.[0] ?? null)}
                required
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={isLoading}>
                {isLoading ? 'Importing...' : 'Import'}
              </Button>
            </DialogFooter>
          </form>
        ) : (
          <div className="space-y-4">
            <Alert className="bg-green-50 border-green-200 text-green-800">
              <AlertDescription>
                <h3 className="font-semibold mb-2">Import Complete</h3>
                <ul className="list-disc list-inside">
                  <li>Created: {importResult.created}</li>
                  <li>Skipped: {importResult.skipped}</li>
                  <li>Failed: {importResult.failed}</li>
                </ul>
              </AlertDescription>
            </Alert>

            {importResult.errors.length > 0 && (
              <div className="bg-red-50 p-4 rounded-md max-h-[200px] overflow-y-auto">
                <h4 className="text-red-800 font-semibold mb-2">Errors:</h4>
                <ul className="list-disc list-inside text-sm text-red-700">
                  {importResult.errors.map((err, index) => (
                    <li key={index}>{err}</li>
                  ))}
                </ul>
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}


