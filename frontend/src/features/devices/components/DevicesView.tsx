import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { ChevronDown, Plus, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { apiClient } from '@/api/client'
import type { DeviceImportSummary } from '@/types'
import { Device, DeviceFormData, DeviceSearchField } from '../types'
import { DeviceFilters } from './DeviceFilters'
import { DeviceTable } from './DeviceTable'
import { DeviceFormDialog } from './DeviceFormDialog'
import { DeviceImportDialog } from './DeviceImportDialog'
import { DeviceDeleteDialog } from './DeviceDeleteDialog'
import { DeviceTerminalDialog } from './DeviceTerminalDialog'
import { ConfigHistoryDialog } from './ConfigHistoryDialog'
import { useAuthStore } from '@/store/authStore'

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
  const [terminalDevice, setTerminalDevice] = useState<Device | null>(null)
  const [historyDevice, setHistoryDevice] = useState<Device | null>(null)
  const currentUser = useAuthStore((s) => s.user)

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

  const createDeviceMutation = useMutation({
    mutationFn: (payload: DeviceFormData) => apiClient.createDevice(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      setDialogState((state) => ({ ...state, add: false }))
      setFormData(initialForm)
      toast.success('Device created successfully')
    },
    onError: (err: any) => {
      const message = err.response?.data?.detail || 'Failed to create device'
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
    onError: (err: any) => {
      const message = err.response?.data?.detail || 'Failed to update device'
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
    onError: (err: any) => {
      const message = err.response?.data?.detail || 'Failed to delete device'
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
    onError: (err: any) => {
      const message = err.response?.data?.detail || 'Failed to recover device'
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
    return <div>Loading devices...</div>
  }

  if (queryError) {
    return <div className="text-red-500">Error loading devices</div>
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
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Devices</h1>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              New device
              <ChevronDown className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuItem onSelect={openAddDialog}>
              <Plus className="mr-2 h-4 w-4" />
              Add device
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
      </div>

      <Card>
        <CardContent className="pt-6">
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

      <Card>
        <CardContent className="p-0">
          <DeviceTable
            devices={filteredDevices}
            onEdit={openEditDialog}
            onDelete={openDeleteDialog}
            onOpenTerminal={(device) => setTerminalDevice(device)}
            onConfigHistory={(device) => setHistoryDevice(device)}
            onRecover={(device) => recoverDeviceMutation.mutate(device)}
            currentUserRole={currentUser?.role ?? null}
          />
        </CardContent>
      </Card>

      <div className="text-sm text-muted-foreground">
        Showing {filteredDevices.length} of {totalDevices} devices
      </div>

      <DeviceFormDialog
        open={dialogState.add}
        title="Add New Device"
        description="Create a new network device."
        submitLabel="Create Device"
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
        title="Edit Device"
        description="Update device details."
        submitLabel="Update Device"
        formData={formData}
        credentials={credentials}
        isLoading={updateDeviceMutation.isPending}
        error={error}
        onClose={() => setDialogState((state) => ({ ...state, edit: false }))}
        onChange={(values) => setFormData((prev) => ({ ...prev, ...values }))}
        onSubmit={(payload) => {
          setError('')
          updateDeviceMutation.mutate(payload)
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
