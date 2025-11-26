import { useState, useMemo } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChevronDown, Plus, Upload, Server, Wifi, WifiOff, Building2, X, Terminal, Trash2 } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { PageHeader } from '@/components/layout/page-header'
import { apiClient } from '@/api/client'
import type { Device, DeviceFormData, DeviceImportSummary, DeviceSearchField } from '../types'
import { DeviceFilters } from './DeviceFilters'
import { DeviceTable } from './DeviceTable'
import { DeviceFormDialog } from './DeviceFormDialog'
import { DeviceImportDialog } from './DeviceImportDialog'
import { DeviceDeleteDialog } from './DeviceDeleteDialog'
import { DeviceTerminalDialog } from './DeviceTerminalDialog'
import { ConfigHistoryDialog } from './ConfigHistoryDialog'
import { useAuthStore, selectCanModify } from '@/store/authStore'

const initialForm: DeviceFormData = {
  hostname: '',
  mgmt_ip: '',
  vendor: '',
  platform: '',
  role: '',
  site: '',
  credentials_ref: 0,
}

export function DevicesView() {
  const [filters, setFilters] = useState({
    search: '',
    searchFields: ['hostname', 'mgmt_ip'] as DeviceSearchField[],
    showDisabled: false,
  })
  const [formData, setFormData] = useState<DeviceFormData>(initialForm)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importResult, setImportResult] = useState<DeviceImportSummary | null>(null)
  const [error, setError] = useState('')
  const [dialogState, setDialogState] = useState({
    add: false,
    edit: false,
    import: false,
    delete: false,
  })
  const [deviceToDelete, setDeviceToDelete] = useState<Device | null>(null)
  const [deviceToEdit, setDeviceToEdit] = useState<Device | null>(null)
  const [terminalDevice, setTerminalDevice] = useState<Device | null>(null)
  const [historyDevice, setHistoryDevice] = useState<Device | null>(null)
  const [selectedDeviceIds, setSelectedDeviceIds] = useState<Set<number>>(new Set())
  const currentUser = useAuthStore((s) => s.user)
  const canModify = useAuthStore(selectCanModify)

  const queryClient = useQueryClient()

  const { data, isLoading, error: queryError } = useQuery({
    queryKey: ['devices', filters.showDisabled],
    queryFn: () =>
      apiClient.getDevices({
        enabled: filters.showDisabled ? undefined : true,
      }),
    refetchInterval: 5000,
  })

  const { data: credentials } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => apiClient.getCredentials(),
  })

  // Create a map of credential ID to name for display
  const credentialMap = useMemo(() => {
    const map: Record<number, string> = {}
    if (credentials) {
      for (const cred of credentials) {
        map[cred.id] = cred.name
      }
    }
    return map
  }, [credentials])

  // Compute stats
  const stats = useMemo(() => {
    const devices = data?.devices ?? []
    const enabledDevices = devices.filter((d) => d.enabled)
    const reachable = enabledDevices.filter((d) => d.reachability_status === 'reachable').length
    const unreachable = enabledDevices.filter((d) => d.reachability_status === 'unreachable').length
    const unknown = enabledDevices.filter(
      (d) => !d.reachability_status || d.reachability_status === 'unknown'
    ).length
    const vendors = new Set(devices.map((d) => d.vendor)).size
    const sites = new Set(devices.map((d) => d.site).filter(Boolean)).size

    return {
      total: devices.length,
      enabled: enabledDevices.length,
      reachable,
      unreachable,
      unknown,
      vendors,
      sites,
    }
  }, [data])

  const createDeviceMutation = useMutation({
    mutationFn: (payload: DeviceFormData) => apiClient.createDevice(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      setDialogState((state) => ({ ...state, add: false }))
      setFormData(initialForm)
      toast.success('Device created successfully')
    },
    onError: (err: Error & { message?: string }) => {
      const message = err.message || 'Failed to create device'
      setError(message)
      toast.error(message)
    },
  })

  const updateDeviceMutation = useMutation({
    mutationFn: (payload: DeviceFormData) => apiClient.updateDevice(payload.id!, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      setDialogState((state) => ({ ...state, edit: false }))
      setFormData(initialForm)
      toast.success('Device updated successfully')
    },
    onError: (err: Error & { message?: string }) => {
      const message = err.message || 'Failed to update device'
      setError(message)
      toast.error(message)
    },
  })

  const deleteDeviceMutation = useMutation({
    mutationFn: (id: number) => apiClient.deleteDevice(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      setDialogState((state) => ({ ...state, delete: false }))
      toast.success('Device deleted successfully')
    },
    onError: (err: Error & { message?: string }) => {
      const message = err.message || 'Failed to delete device'
      toast.error(message)
    },
  })

  const toggleEnabledMutation = useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      apiClient.updateDevice(id, { enabled }),
    onSuccess: (_, { enabled }) => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      if (deviceToEdit) {
        setDeviceToEdit({ ...deviceToEdit, enabled })
      }
      toast.success(enabled ? 'Device enabled' : 'Device disabled')
    },
    onError: (err: Error & { message?: string }) => {
      const message = err.message || 'Failed to update device'
      toast.error(message)
    },
  })

  const recoverDeviceMutation = useMutation({
    mutationFn: (device: Device) =>
      apiClient.updateDevice(device.id, {
        enabled: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      toast.success('Device recovered')
    },
    onError: (err: Error & { message?: string }) => {
      const message = err.message || 'Failed to recover device'
      toast.error(message)
    },
  })

  const importDevicesMutation = useMutation({
    mutationFn: (file: File) => apiClient.importDevices(file),
    onSuccess: (summary: DeviceImportSummary) => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      setImportResult(summary)
      toast.success(`Imported ${summary.created} devices`)
    },
    onError: (err: Error & { data?: { detail?: string } }) => {
      const message = err.data?.detail || err.message || 'Failed to import devices'
      setError(message)
      toast.error(message)
    },
  })

  const openAddDialog = () => {
    setFormData(initialForm)
    setError('')
    setDialogState((state) => ({ ...state, add: true }))
  }

  const openEditDialog = (device: Device) => {
    setDeviceToEdit(device)
    setFormData({
      id: device.id,
      hostname: device.hostname,
      mgmt_ip: device.mgmt_ip,
      vendor: device.vendor,
      platform: device.platform,
      role: device.role ?? '',
      site: device.site ?? '',
      credentials_ref: device.credentials_ref,
    })
    setError('')
    setDialogState((state) => ({ ...state, edit: true }))
  }

  const openDeleteDialog = (device: Device) => {
    setDeviceToDelete(device)
    setDialogState((state) => ({ ...state, delete: true }))
  }

  const resetImportDialog = () => {
    setImportFile(null)
    setImportResult(null)
    setError('')
  }

  const handleImportSubmit = () => {
    setError('')
    if (importFile) {
      importDevicesMutation.mutate(importFile)
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Devices"
          description="Manage and monitor your network device inventory"
        />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (queryError) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-destructive">Error loading devices</div>
      </div>
    )
  }

  const devices = data?.devices ?? []
  const totalDevices = data?.total ?? devices.length

  const getFieldValue = (device: Device, field: DeviceSearchField): string | null => {
    switch (field) {
      case 'hostname':
        return device.hostname
      case 'mgmt_ip':
        return device.mgmt_ip
      case 'vendor':
        return device.vendor
      case 'platform':
        return device.platform
      case 'role':
        return device.role ?? null
      case 'site':
        return device.site ?? null
      case 'reachability_status':
        return device.reachability_status ?? null
      case 'status':
        return device.enabled ? 'enabled' : 'disabled'
      default:
        return null
    }
  }

  const fuzzyIncludes = (query: string, value: string) => {
    if (!query) return true
    let qi = 0
    const q = query.toLowerCase()
    const v = value.toLowerCase()
    for (const char of v) {
      if (char === q[qi]) {
        qi += 1
        if (qi === q.length) return true
      }
    }
    return v.includes(q)
  }

  const filteredDevices = filters.search
    ? devices.filter((device) => {
        const query = filters.search.trim().toLowerCase()
        if (!query) return true
        return filters.searchFields.some((field) => {
          const value = getFieldValue(device, field)
          if (!value) return false
          const normalized = value.toLowerCase()
          return normalized.includes(query) || fuzzyIncludes(query, normalized)
        })
      })
    : devices

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Devices"
        description="Manage and monitor your network device inventory"
        actions={
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button className="gap-2" disabled={!canModify} title={!canModify ? 'Viewers cannot add devices' : undefined}>
                <Plus className="h-4 w-4" />
                Add Device
                <ChevronDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuItem onSelect={openAddDialog}>
                <Plus className="mr-2 h-4 w-4" />
                Add single device
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={() =>
                  setDialogState((state) => ({
                    ...state,
                    import: true,
                  }))
                }
              >
                <Upload className="mr-2 h-4 w-4" />
                Import from CSV
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Devices</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.total}</div>
            <p className="text-xs text-muted-foreground">
              {stats.enabled} enabled, {stats.total - stats.enabled} disabled
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Reachable</CardTitle>
            <Wifi className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.reachable}</div>
            <p className="text-xs text-muted-foreground">
              {stats.enabled > 0
                ? `${Math.round((stats.reachable / stats.enabled) * 100)}% of enabled devices`
                : 'No enabled devices'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Unreachable</CardTitle>
            <WifiOff className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{stats.unreachable}</div>
            <p className="text-xs text-muted-foreground">
              {stats.unknown > 0 ? `${stats.unknown} unknown status` : 'All devices checked'}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Infrastructure</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.vendors}</div>
            <p className="text-xs text-muted-foreground">
              {stats.vendors === 1 ? 'vendor' : 'vendors'} across {stats.sites}{' '}
              {stats.sites === 1 ? 'site' : 'sites'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-3">
          <div>
            <CardTitle className="text-base">Filter Devices</CardTitle>
            <CardDescription>Search and filter your device inventory</CardDescription>
          </div>
        </CardHeader>
        <CardContent className="pt-0">
          <DeviceFilters
            search={filters.search}
            searchFields={filters.searchFields}
            showDisabled={filters.showDisabled}
            onChange={(values) =>
              setFilters((prev) => ({
                ...prev,
                ...values,
                searchFields:
                  values.searchFields !== undefined
                    ? values.searchFields.length
                      ? values.searchFields
                      : ['hostname']
                    : prev.searchFields,
              }))
            }
          />
        </CardContent>
      </Card>

      {/* Device Table */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Device Inventory</CardTitle>
              <CardDescription>
                Showing {filteredDevices.length} of {totalDevices} devices
              </CardDescription>
            </div>
            <div className="hidden sm:flex items-center gap-1 text-xs text-muted-foreground">
              <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">j</kbd>
              <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">k</kbd>
              <span>navigate</span>
              <span className="mx-1">|</span>
              <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">Enter</kbd>
              <span>edit</span>
              <span className="mx-1">|</span>
              <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">t</kbd>
              <span>terminal</span>
              <span className="mx-1">|</span>
              <kbd className="px-1.5 py-0.5 bg-muted rounded text-[10px] font-mono">f</kbd>
              <span>favorite</span>
            </div>
          </div>
        </CardHeader>
        {selectedDeviceIds.size > 0 && (
          <div className="border-b bg-muted/30 px-4 py-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium">{selectedDeviceIds.size} device{selectedDeviceIds.size !== 1 ? 's' : ''} selected</span>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    // Open terminal for first selected device
                    const device = filteredDevices.find((d) => selectedDeviceIds.has(d.id))
                    if (device) setTerminalDevice(device)
                  }}
                  disabled={selectedDeviceIds.size !== 1 || !canModify}
                  title={!canModify ? 'Viewers cannot open terminal' : undefined}
                >
                  <Terminal className="h-4 w-4 mr-1" />
                  Terminal
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-destructive hover:text-destructive"
                  onClick={() => {
                    // For now just clear selection - could implement bulk delete
                    toast.info('Bulk delete coming soon')
                  }}
                  disabled={!canModify}
                  title={!canModify ? 'Viewers cannot delete devices' : undefined}
                >
                  <Trash2 className="h-4 w-4 mr-1" />
                  Delete
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setSelectedDeviceIds(new Set())}
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        )}
        <CardContent className="p-0">
          <DeviceTable
            devices={filteredDevices}
            credentialMap={credentialMap}
            selectedIds={selectedDeviceIds}
            onSelectionChange={setSelectedDeviceIds}
            onEdit={openEditDialog}
            onDelete={openDeleteDialog}
            onOpenTerminal={(device) => setTerminalDevice(device)}
            onConfigHistory={(device) => setHistoryDevice(device)}
            onRecover={(device) => recoverDeviceMutation.mutate(device)}
            currentUserRole={currentUser?.role ?? null}
          />
        </CardContent>
      </Card>

      <DeviceFormDialog
        open={dialogState.add}
        mode="create"
        formData={formData}
        credentials={credentials}
        isLoading={createDeviceMutation.isPending}
        error={error}
        onClose={() => setDialogState((state) => ({ ...state, add: false }))}
        onChange={(values) => setFormData((prev) => ({ ...prev, ...values }))}
        onSubmit={(payload) => {
          setError('')
          createDeviceMutation.mutate(payload)
        }}
      />

      <DeviceFormDialog
        open={dialogState.edit}
        mode="edit"
        formData={formData}
        device={deviceToEdit}
        credentials={credentials}
        isLoading={updateDeviceMutation.isPending}
        error={error}
        onClose={() => {
          setDialogState((state) => ({ ...state, edit: false }))
          setDeviceToEdit(null)
        }}
        onChange={(values) => setFormData((prev) => ({ ...prev, ...values }))}
        onSubmit={(payload) => {
          setError('')
          updateDeviceMutation.mutate(payload)
        }}
        onToggleEnabled={(enabled) => {
          if (deviceToEdit) {
            toggleEnabledMutation.mutate({ id: deviceToEdit.id, enabled })
          }
        }}
      />

      <DeviceImportDialog
        open={dialogState.import}
        error={error}
        isLoading={importDevicesMutation.isPending}
        importResult={importResult}
        onClose={() => {
          resetImportDialog()
          setDialogState((state) => ({ ...state, import: false }))
        }}
        onFileChange={(file) => setImportFile(file)}
        onSubmit={handleImportSubmit}
      />

      <DeviceDeleteDialog
        open={dialogState.delete}
        device={deviceToDelete}
        onCancel={() => setDialogState((state) => ({ ...state, delete: false }))}
        onConfirm={() => {
          if (deviceToDelete) {
            deleteDeviceMutation.mutate(deviceToDelete.id)
          }
        }}
      />

      <DeviceTerminalDialog
        open={Boolean(terminalDevice)}
        device={terminalDevice}
        onClose={() => setTerminalDevice(null)}
      />

      <ConfigHistoryDialog
        open={Boolean(historyDevice)}
        deviceId={historyDevice?.id ?? null}
        hostname={historyDevice?.hostname}
        onClose={() => setHistoryDevice(null)}
      />
    </div>
  )
}
