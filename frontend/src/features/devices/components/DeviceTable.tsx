import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { type Device } from '../types'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
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
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import {
  MoreHorizontal,
  Pencil,
  ScrollText,
  Terminal,
  Trash2,
  RotateCcw,
  Server,
  Key,
  Copy,
  Check,
  Star,
  ExternalLink,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/store/uiStore'

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation()
    await navigator.clipboard.writeText(value)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <TooltipProvider delayDuration={0}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
            onClick={handleCopy}
          >
            {copied ? (
              <Check className="h-3 w-3 text-green-500" />
            ) : (
              <Copy className="h-3 w-3 text-muted-foreground" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="top" className="text-xs">
          {copied ? 'Copied!' : 'Copy'}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

interface DeviceTableProps {
  devices: Device[]
  credentialMap?: Record<number, string>
  selectedIds?: Set<number>
  onSelectionChange?: (ids: Set<number>) => void
  onEdit: (device: Device) => void
  onDelete: (device: Device) => void
  onOpenTerminal: (device: Device) => void
  onConfigHistory: (device: Device) => void
  onRecover: (device: Device) => void
  currentUserRole: string | null
}

/** Check if user can modify (admin or operator) */
function canModifyForRole(role: string | null): boolean {
  return role === 'admin' || role === 'operator'
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
  selectedIds = new Set(),
  onSelectionChange,
  onEdit,
  onDelete,
  onOpenTerminal,
  onConfigHistory,
  onRecover,
  currentUserRole,
}: DeviceTableProps) {
  const [selectedIndex, setSelectedIndex] = useState<number>(-1)
  const tableRef = useRef<HTMLTableElement>(null)
  const rowRefs = useRef<Map<number, HTMLTableRowElement>>(new Map())
  const { favoriteDeviceIds, toggleFavoriteDevice } = useUIStore()

  // Sort devices: favorites first, then by hostname
  const sortedDevices = [...devices].sort((a, b) => {
    const aFav = favoriteDeviceIds.has(a.id)
    const bFav = favoriteDeviceIds.has(b.id)
    if (aFav && !bFav) return -1
    if (!aFav && bFav) return 1
    return 0
  })
  
  const enabledDevices = sortedDevices.filter((d) => d.enabled)
  const allEnabledSelected = enabledDevices.length > 0 && enabledDevices.every((d) => selectedIds.has(d.id))
  const someSelected = selectedIds.size > 0

  const handleSelectAll = (checked: boolean) => {
    if (!onSelectionChange) return
    if (checked) {
      onSelectionChange(new Set(enabledDevices.map((d) => d.id)))
    } else {
      onSelectionChange(new Set())
    }
  }

  const handleSelectOne = (device: Device, checked: boolean) => {
    if (!onSelectionChange) return
    const next = new Set(selectedIds)
    if (checked) {
      next.add(device.id)
    } else {
      next.delete(device.id)
    }
    onSelectionChange(next)
  }

  // Reset selection when devices change
  useEffect(() => {
    setSelectedIndex(-1)
  }, [devices])

  // Scroll selected row into view
  useEffect(() => {
    if (selectedIndex >= 0 && selectedIndex < sortedDevices.length) {
      const row = rowRefs.current.get(selectedIndex)
      row?.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
    }
  }, [selectedIndex, sortedDevices.length])

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Only handle if table is focused or no input element is focused
      const activeElement = document.activeElement
      const isInputFocused =
        activeElement instanceof HTMLInputElement ||
        activeElement instanceof HTMLTextAreaElement ||
        activeElement instanceof HTMLSelectElement ||
        activeElement?.getAttribute('contenteditable') === 'true'

      if (isInputFocused) return
      if (sortedDevices.length === 0) return

      const selectedDevice = selectedIndex >= 0 ? sortedDevices[selectedIndex] : null
      const canModify = canModifyForRole(currentUserRole)

      switch (e.key) {
        case 'j':
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => Math.min(prev + 1, sortedDevices.length - 1))
          break
        case 'k':
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => Math.max(prev - 1, 0))
          break
        case 'g':
          // gg to go to top (check if g was pressed before)
          if (e.repeat) {
            e.preventDefault()
            setSelectedIndex(0)
          }
          break
        case 'G':
          e.preventDefault()
          setSelectedIndex(sortedDevices.length - 1)
          break
        case 'Enter':
          if (selectedDevice?.enabled && canModify) {
            e.preventDefault()
            onEdit(selectedDevice)
          }
          break
        case 't':
          if (selectedDevice?.enabled && canModify) {
            e.preventDefault()
            onOpenTerminal(selectedDevice)
          }
          break
        case 'c':
          if (selectedDevice?.enabled) {
            e.preventDefault()
            onConfigHistory(selectedDevice)
          }
          break
        case 'f':
          if (selectedDevice) {
            e.preventDefault()
            toggleFavoriteDevice(selectedDevice.id)
          }
          break
        case 'Escape':
          e.preventDefault()
          setSelectedIndex(-1)
          break
      }
    },
    [sortedDevices, selectedIndex, onEdit, onOpenTerminal, onConfigHistory, toggleFavoriteDevice, currentUserRole]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])

  return (
    <Table ref={tableRef}>
      <TableHeader>
        <TableRow>
          {onSelectionChange && (
            <TableHead className="w-[40px]">
              <Checkbox
                checked={allEnabledSelected}
                onCheckedChange={handleSelectAll}
                aria-label="Select all devices"
                className={cn(someSelected && !allEnabledSelected && 'data-[state=checked]:bg-primary/50')}
                {...(someSelected && !allEnabledSelected ? { 'data-state': 'indeterminate' } : {})}
              />
            </TableHead>
          )}
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
        {sortedDevices.length > 0 ? (
          sortedDevices.map((device, index) => {
            const credentialName = credentialMap[device.credentials_ref]
            const isSelected = index === selectedIndex
            const isChecked = selectedIds.has(device.id)
            const isFavorite = favoriteDeviceIds.has(device.id)
            return (
              <TableRow
                key={device.id}
                ref={(el) => {
                  if (el) rowRefs.current.set(index, el)
                  else rowRefs.current.delete(index)
                }}
                className={cn(
                  !device.enabled && 'opacity-60',
                  isSelected && 'bg-muted/50 ring-1 ring-inset ring-primary/20',
                  isChecked && 'bg-primary/5'
                )}
                onClick={() => setSelectedIndex(index)}
                tabIndex={0}
              >
                {onSelectionChange && (
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <Checkbox
                      checked={isChecked}
                      disabled={!device.enabled}
                      onCheckedChange={(checked) => handleSelectOne(device, checked === true)}
                      aria-label={`Select ${device.hostname}`}
                    />
                  </TableCell>
                )}
                <TableCell>
                  <div className="flex items-center gap-2 group">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0"
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleFavoriteDevice(device.id)
                      }}
                    >
                      <Star
                        className={cn(
                          'h-4 w-4 transition-colors',
                          isFavorite
                            ? 'fill-yellow-400 text-yellow-400'
                            : 'text-muted-foreground hover:text-yellow-400'
                        )}
                      />
                    </Button>
                    <Server className="h-4 w-4 text-muted-foreground" />
                    <div className="flex items-center gap-1">
                      <div>
                        <Link
                          to={`/devices/${device.id}`}
                          className="font-medium hover:text-primary hover:underline"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {device.hostname}
                        </Link>
                        <div className="text-xs text-muted-foreground">
                          {device.vendor} / {device.platform}
                        </div>
                      </div>
                      <CopyButton value={device.hostname} />
                    </div>
                  </div>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1 group">
                    <code className="text-sm bg-muted px-2 py-0.5 rounded">{device.mgmt_ip}</code>
                    <CopyButton value={device.mgmt_ip} />
                  </div>
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
                  <div className="flex flex-col items-start gap-1">
                    <Badge
                      variant={device.enabled ? 'outline' : 'destructive'}
                      className={device.enabled ? 'border-green-500 text-green-600 bg-green-50' : ''}
                    >
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
                      <DropdownMenuItem asChild>
                        <Link to={`/devices/${device.id}`}>
                          <ExternalLink className="mr-2 h-4 w-4" />
                          View details
                        </Link>
                      </DropdownMenuItem>
                      <DropdownMenuItem onSelect={() => onEdit(device)} disabled={!device.enabled || !canModifyForRole(currentUserRole)}>
                        <Pencil className="mr-2 h-4 w-4" />
                        Edit details
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        onSelect={() => onOpenTerminal(device)}
                        disabled={!device.enabled || !canModifyForRole(currentUserRole)}
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
                        disabled={!device.enabled || !canModifyForRole(currentUserRole)}
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
            <TableCell colSpan={onSelectionChange ? 9 : 8} className="text-center h-24 text-muted-foreground">
              No devices found
            </TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  )
}
