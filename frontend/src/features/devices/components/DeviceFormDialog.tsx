import { DeviceFormData } from '../types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { FormEvent } from 'react'

const SUPPORTED_VENDORS = ['cisco', 'juniper', 'arista', 'hp', 'huawei', 'linux']
const SUPPORTED_PLATFORMS = ['ios', 'iosxe', 'nxos', 'junos', 'eos', 'comware', 'vrp', 'linux']

interface DeviceFormDialogProps {
  open: boolean
  title: string
  description: string
  submitLabel: string
  formData: DeviceFormData
  credentials?: Array<{ id: number; name: string }>
  isLoading: boolean
  error?: string
  onClose: () => void
  onChange: (values: Partial<DeviceFormData>) => void
  onSubmit: (data: DeviceFormData) => void
}

export function DeviceFormDialog({
  open,
  title,
  description,
  submitLabel,
  formData,
  credentials = [],
  isLoading,
  error,
  onClose,
  onChange,
  onSubmit,
}: DeviceFormDialogProps) {
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit(formData)
  }

  return (
    <Dialog open={open} onOpenChange={(value) => !value && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="hostname">Hostname</Label>
              <Input
                id="hostname"
                value={formData.hostname}
                onChange={(e) => onChange({ hostname: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="mgmt_ip">Management IP</Label>
              <Input
                id="mgmt_ip"
                value={formData.mgmt_ip}
                onChange={(e) => onChange({ mgmt_ip: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Vendor</Label>
              <Select
                value={formData.vendor}
                onValueChange={(value) => onChange({ vendor: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select vendor" />
                </SelectTrigger>
                <SelectContent>
                  {SUPPORTED_VENDORS.map((vendor) => (
                    <SelectItem key={vendor} value={vendor}>
                      {vendor.toUpperCase()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Platform</Label>
              <Select
                value={formData.platform}
                onValueChange={(value) => onChange({ platform: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select platform" />
                </SelectTrigger>
                <SelectContent>
                  {SUPPORTED_PLATFORMS.map((platform) => (
                    <SelectItem key={platform} value={platform}>
                      {platform.toUpperCase()}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                value={formData.role}
                onChange={(e) => onChange({ role: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="site">Site</Label>
              <Input
                id="site"
                value={formData.site}
                onChange={(e) => onChange({ site: e.target.value })}
              />
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>Credential</Label>
              <Select
                value={String(formData.credentials_ref ?? '')}
                onValueChange={(value) => onChange({ credentials_ref: Number(value) })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select credential" />
                </SelectTrigger>
                <SelectContent>
                  {credentials.map((credential) => (
                    <SelectItem key={credential.id} value={String(credential.id)}>
                      {credential.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
              {isLoading ? 'Saving...' : submitLabel}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}


