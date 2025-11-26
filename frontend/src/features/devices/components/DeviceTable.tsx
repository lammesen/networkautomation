import { Device } from '../types'
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
} from 'lucide-react'

interface DeviceTableProps {
  devices: Device[]
  onEdit: (device: Device) => void
  onDelete: (device: Device) => void
  onOpenTerminal: (device: Device) => void
  onConfigHistory: (device: Device) => void
  onRecover: (device: Device) => void
  currentUserRole: string | null
}

export function DeviceTable({
  devices,
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
          <TableHead>Hostname</TableHead>
          <TableHead>IP Address</TableHead>
          <TableHead>Vendor</TableHead>
          <TableHead>Platform</TableHead>
          <TableHead>Role</TableHead>
          <TableHead>Site</TableHead>
          <TableHead>Reachability</TableHead>
          <TableHead>Status</TableHead>
          <TableHead className="text-right">Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {devices.length > 0 ? (
          devices.map((device) => (
            <TableRow key={device.id}>
              <TableCell className="font-medium">{device.hostname}</TableCell>
              <TableCell>{device.mgmt_ip}</TableCell>
              <TableCell>{device.vendor}</TableCell>
              <TableCell>{device.platform}</TableCell>
              <TableCell>{device.role || '-'}</TableCell>
              <TableCell>{device.site || '-'}</TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      device.reachability_status === 'reachable'
                        ? 'bg-green-500'
                        : device.reachability_status === 'unreachable'
                          ? 'bg-red-500'
                          : 'bg-gray-300'
                    }`}
                  />
                  <span className="text-xs text-muted-foreground capitalize">
                    {device.reachability_status || 'unknown'}
                  </span>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant={device.enabled ? 'default' : 'destructive'}>
                  {device.enabled ? 'Enabled' : 'Disabled'}
                </Badge>
                {device.tags?.facts && (
                  <div className="text-xs text-muted-foreground mt-1">
                    {device.tags.facts.model || ''} {device.tags.facts.os_version ? `• ${device.tags.facts.os_version}` : ''}
                  </div>
                )}
              </TableCell>
              <TableCell className="text-right">
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
          ))
        ) : (
          <TableRow>
            <TableCell colSpan={9} className="text-center h-24 text-muted-foreground">
              No devices found
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}
