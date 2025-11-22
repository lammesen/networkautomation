import { Device } from '../types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

interface DeviceTableProps {
  devices: Device[]
  onEdit: (device: Device) => void
  onDelete: (device: Device) => void
  onOpenTerminal: (device: Device) => void
}

export function DeviceTable({ devices, onEdit, onDelete, onOpenTerminal }: DeviceTableProps) {
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
          <TableHead>Actions</TableHead>
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
              </TableCell>
              <TableCell>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => onEdit(device)}>
                    Edit
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => onOpenTerminal(device)}
                    disabled={!device.enabled}
                    title={device.enabled ? 'Open interactive terminal' : 'Enable the device before opening a terminal'}
                  >
                    Terminal
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => onDelete(device)}>
                    Delete
                  </Button>
                </div>
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


