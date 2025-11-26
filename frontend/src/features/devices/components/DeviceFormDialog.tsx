import { type DeviceFormData, type Device } from '../types'
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Switch } from '@/components/ui/switch'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { type FormEvent, useState } from 'react'
import { formatDateTime } from '@/lib/formatters'
import {
  Server,
  Network,
  Building2,
  Settings,
  Wifi,
  WifiOff,
  CircleHelp,
} from 'lucide-react'

const SUPPORTED_VENDORS = ['cisco', 'juniper', 'arista', 'hp', 'huawei', 'linux']
const SUPPORTED_PLATFORMS = ['ios', 'iosxe', 'nxos', 'junos', 'eos', 'comware', 'vrp', 'linux']

interface DeviceFormDialogProps {
  open: boolean
  mode: 'create' | 'edit'
  formData: DeviceFormData
  device?: Device | null
  credentials?: Array<{ id: number; name: string }>
  isLoading: boolean
  error?: string
  onClose: () => void
  onChange: (values: Partial<DeviceFormData>) => void
  onSubmit: (data: DeviceFormData) => void
  onToggleEnabled?: (enabled: boolean) => void
}

function ReachabilityBadge({ status }: { status?: string | null }) {
  if (status === 'reachable') {
    return (
      <Badge variant="outline" className="gap-1 text-green-600 border-green-200 bg-green-50">
        <Wifi className="h-3 w-3" />
        Reachable
      </Badge>
    )
  }
  if (status === 'unreachable') {
    return (
      <Badge variant="outline" className="gap-1 text-red-600 border-red-200 bg-red-50">
        <WifiOff className="h-3 w-3" />
        Unreachable
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="gap-1 text-muted-foreground">
      <CircleHelp className="h-3 w-3" />
      Unknown
    </Badge>
  )
}

export function DeviceFormDialog({
  open,
  mode,
  formData,
  device,
  credentials = [],
  isLoading,
  error,
  onClose,
  onChange,
  onSubmit,
  onToggleEnabled,
}: DeviceFormDialogProps) {
  const [activeTab, setActiveTab] = useState('general')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    onSubmit(formData)
  }

  const isEditMode = mode === 'edit'
  const title = isEditMode ? 'Edit Device' : 'Add New Device'
  const description = isEditMode
    ? 'Update device configuration and settings.'
    : 'Add a new network device to your inventory.'
  const submitLabel = isEditMode ? 'Save Changes' : 'Create Device'

  return (
    <Dialog
      open={open}
      onOpenChange={(value) => {
        if (!value) {
          onClose()
          setActiveTab('general')
        }
      }}
    >
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Server className="h-5 w-5" />
            {title}
          </DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        {isEditMode && device && (
          <div className="flex items-center justify-between py-2 px-3 bg-muted/50 rounded-lg">
            <div className="flex items-center gap-4">
              <ReachabilityBadge status={device.reachability_status} />
              {device.last_reachability_check && (
                <span className="text-xs text-muted-foreground">
                  Last checked: {formatDateTime(device.last_reachability_check)}
                </span>
              )}
            </div>
            <Badge variant={device.enabled ? 'default' : 'secondary'}>
              {device.enabled ? 'Enabled' : 'Disabled'}
            </Badge>
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex flex-col flex-1 overflow-hidden">
          <Tabs
            value={activeTab}
            onValueChange={setActiveTab}
            className="flex flex-col flex-1 overflow-hidden"
          >
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="general" className="gap-1.5">
                <Server className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">General</span>
              </TabsTrigger>
              <TabsTrigger value="network" className="gap-1.5">
                <Network className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Network</span>
              </TabsTrigger>
              <TabsTrigger value="organization" className="gap-1.5">
                <Building2 className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Organization</span>
              </TabsTrigger>
              <TabsTrigger value="settings" className="gap-1.5">
                <Settings className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">Settings</span>
              </TabsTrigger>
            </TabsList>

            <div className="flex-1 overflow-y-auto py-4">
              <TabsContent value="general" className="mt-0 space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="hostname">Hostname</Label>
                    <Input
                      id="hostname"
                      placeholder="e.g. router-core-01"
                      value={formData.hostname}
                      onChange={(e) => onChange({ hostname: e.target.value })}
                      required
                    />
                    <p className="text-xs text-muted-foreground">
                      A unique identifier for this device in your network
                    </p>
                  </div>

                  <Separator />

                  <div className="grid grid-cols-2 gap-4">
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
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="network" className="mt-0 space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="mgmt_ip">Management IP / Hostname</Label>
                    <Input
                      id="mgmt_ip"
                      placeholder="e.g. 192.168.1.1 or device.example.com"
                      value={formData.mgmt_ip}
                      onChange={(e) => onChange({ mgmt_ip: e.target.value })}
                      required
                    />
                    <p className="text-xs text-muted-foreground">
                      The IP address or DNS hostname used to connect to this device
                    </p>
                  </div>

                  <Separator />

                  <div className="space-y-2">
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
                    <p className="text-xs text-muted-foreground">
                      SSH credentials used to authenticate with this device
                    </p>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="organization" className="mt-0 space-y-4">
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="site">Site</Label>
                    <Input
                      id="site"
                      placeholder="e.g. datacenter-east, branch-nyc"
                      value={formData.site}
                      onChange={(e) => onChange({ site: e.target.value })}
                    />
                    <p className="text-xs text-muted-foreground">
                      Physical or logical location of the device
                    </p>
                  </div>

                  <Separator />

                  <div className="space-y-2">
                    <Label htmlFor="role">Role</Label>
                    <Input
                      id="role"
                      placeholder="e.g. core, edge, access, lab"
                      value={formData.role}
                      onChange={(e) => onChange({ role: e.target.value })}
                    />
                    <p className="text-xs text-muted-foreground">
                      The function or purpose of this device in your network
                    </p>
                  </div>
                </div>
              </TabsContent>

              <TabsContent value="settings" className="mt-0 space-y-4">
                {isEditMode && device ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between rounded-lg border p-4">
                      <div className="space-y-0.5">
                        <Label htmlFor="enabled" className="text-base">
                          Device Enabled
                        </Label>
                        <p className="text-sm text-muted-foreground">
                          Disabled devices are excluded from automation tasks and monitoring
                        </p>
                      </div>
                      <Switch
                        id="enabled"
                        checked={device.enabled}
                        onCheckedChange={onToggleEnabled}
                      />
                    </div>

                    <Separator />

                    <div className="rounded-lg border p-4 space-y-3">
                      <h4 className="text-sm font-medium">Device Information</h4>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <span className="text-muted-foreground">Device ID</span>
                          <p className="font-mono">{device.id}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Created</span>
                          <p>{device.created_at ? formatDateTime(device.created_at) : '—'}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Last Updated</span>
                          <p>{device.updated_at ? formatDateTime(device.updated_at) : '—'}</p>
                        </div>
                        <div>
                          <span className="text-muted-foreground">Last Reachability Check</span>
                          <p>
                            {device.last_reachability_check
                              ? formatDateTime(device.last_reachability_check)
                              : '—'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground">
                    <Settings className="h-10 w-10 mb-3 opacity-50" />
                    <p>Settings are available after the device is created.</p>
                  </div>
                )}
              </TabsContent>
            </div>
          </Tabs>

          {error && (
            <Alert variant="destructive" className="mt-2">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <DialogFooter className="mt-4 pt-4 border-t">
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
