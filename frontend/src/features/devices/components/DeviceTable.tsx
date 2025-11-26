import { type Device } from '../types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  MoreHorizontal,
  Pencil,
  ScrollText,
  Terminal,
  Trash2,
  RotateCcw,
  Server,
  Key,
} from 'lucide-react'

interface DeviceTableProps {
  devices: Device[]
  credentialMap?: Record<number, string>
  onEdit: (device: Device) => void
  onDelete: (device: Device) => void
  onOpenTerminal: (device: Device) => void
  onConfigHistory: (device: Device) => void
  onRecover: (device: Device) => void
  currentUserRole: string | null
}

function ReachabilityIndicator({ status }: { status: string | null | undefined }) {
  const getStatusConfig = () => {
    switch (status) {
      case 'reachable':
        return { color: 'bg-green-500', label: 'Reachable', textColor: 'text-green-600' }
      case 'unreachable':
        return { color: 'bg-red-500', label: 'Unreachable', textColor: 'text-red-600' }
      default:
        return { color: 'bg-gray-300', label: 'Unknown', textColor: 'text-muted-foreground' }
    }
  }

  const config = getStatusConfig()

  return (
    <div className="flex items-center gap-2">
      <div className={`w-2.5 h-2.5 rounded-full ${config.color}`} />
      <span className={`text-sm ${config.textColor}`}>{config.label}</span>
    </div>
  )
}

export function DeviceTable({
  devices,
  credentialMap = {},
  onEdit,
  onDelete,
  onOpenTerminal,
  onConfigHistory,
  onRecover,
  currentUserRole,
}: DeviceTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Device</TableHead>
          <TableHead>IP Address</TableHead>
          <TableHead>Platform</TableHead>
          <TableHead>Location</TableHead>
          <TableHead>Credentials</TableHead>
          <TableHead>Reachability</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="w-[70px]"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {devices.length > 0 ? (
          devices.map((device) => {
            const credentialName = credentialMap[device.credentials_ref]
            return (
              <TableRow key={device.id} className={!device.enabled ? 'opacity-60' : ''}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Server className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <div className="font-medium">{device.hostname}</div>
                      <div className="text-xs text-muted-foreground">
                        {device.vendor} / {device.platform}
                      </div>
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <code className="text-sm bg-muted px-2 py-0.5 rounded">{device.mgmt_ip}</code>
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="font-normal">
                    {device.platform.toUpperCase()}
                  </Badge>
                </TableCell>
                <TableCell>
                  <div className="text-sm">
                    {device.site || <span className="text-muted-foreground">-</span>}
                  </div>
                  {device.role && (
                    <div className="text-xs text-muted-foreground">{device.role}</div>
                  )}
                </TableCell>
                <TableCell>
                  {credentialName ? (
                    <div className="flex items-center gap-1.5">
                      <Key className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-sm">{credentialName}</span>
                    </div>
                  ) : (
                    <span className="text-muted-foreground text-sm">Unknown</span>
                  )}
                </TableCell>
                <TableCell>
                  <ReachabilityIndicator status={device.reachability_status} />
                </TableCell>
                <TableCell>
                  <div className="flex flex-col gap-1">
                    <Badge variant={device.enabled ? 'default' : 'destructive'}>
                      {device.enabled ? 'Enabled' : 'Disabled'}
                    </Badge>
                    {device.tags &&
                      typeof device.tags === 'object' &&
                      'facts' in device.tags &&
                      device.tags.facts &&
                      typeof device.tags.facts === 'object' && (
                        <div className="text-xs text-muted-foreground">
                          {(device.tags.facts as Record<string, string>).model || ''}{' '}
                          {(device.tags.facts as Record<string, string>).os_version
                            ? `v${(device.tags.facts as Record<string, string>).os_version}`
                            : ''}
                        </div>
                      )}
                  </div>
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <MoreHorizontal className="h-4 w-4" />
                        <span className="sr-only">Open device actions</span>
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className="w-48">
                      <DropdownMenuLabel>Actions</DropdownMenuLabel>
                      <DropdownMenuItem onSelect={() => onEdit(device)} disabled={!device.enabled}>
                        <Pencil className="mr-2 h-4 w-4" />
                        Edit details
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onSelect={() => onOpenTerminal(device)}
                        disabled={!device.enabled}
                      >
                        <Terminal className="mr-2 h-4 w-4" />
                        Open terminal
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onSelect={() => onConfigHistory(device)}
                        disabled={!device.enabled}
                      >
                        <ScrollText className="mr-2 h-4 w-4" />
                        View configs
                      </DropdownMenuItem>
                      {currentUserRole === 'admin' && !device.enabled && (
                        <>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onSelect={() => onRecover(device)}>
                            <RotateCcw className="mr-2 h-4 w-4" />
                            Recover device
                          </DropdownMenuItem>
                        </>
                      )}
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onSelect={() => onDelete(device)}
                        disabled={!device.enabled}
                        className="text-destructive focus:text-destructive"
                      >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            )
          })
        ) : (
          <TableRow>
            <TableCell colSpan={8} className="text-center h-24 text-muted-foreground">
              No devices found
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}
