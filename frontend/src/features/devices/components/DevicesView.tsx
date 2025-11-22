import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { apiClient } from '@/api/client'
import { Device, DeviceFormData } from '../types'
import { DeviceFilters } from './DeviceFilters'
import { DeviceTable } from './DeviceTable'
import { DeviceFormDialog } from './DeviceFormDialog'
import { DeviceImportDialog, DeviceImportSummary } from './DeviceImportDialog'
import { DeviceDeleteDialog } from './DeviceDeleteDialog'
import { DeviceTerminalDialog } from './DeviceTerminalDialog'

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
  const [filters, setFilters] = useState({ site: '', role: '', search: '' })
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

  const queryClient = useQueryClient()

  const { data, isLoading, error: queryError } = useQuery({
    queryKey: ['devices', filters.site, filters.role, filters.search],
    queryFn: () => apiClient.getDevices({ site: filters.site, role: filters.role, search: filters.search }),
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

  const importDevicesMutation = useMutation({
    mutationFn: (file: File) => apiClient.importDevices(file),
    onSuccess: (summary) => {
      queryClient.invalidateQueries({ queryKey: ['devices'] })
      setImportResult(summary)
      toast.success(`Imported ${summary.created} devices`)
    },
    onError: (err: any) => {
      const message = err.response?.data?.detail || 'Failed to import devices'
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
  const totalDevices = data?.total ?? 0

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Devices</h1>
        <div className="flex gap-2">
          <Button onClick={openAddDialog}>Add Device</Button>
          <Button variant="secondary" onClick={() => setDialogState((state) => ({ ...state, import: true }))}>
            Import CSV
          </Button>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <DeviceFilters
            search={filters.search}
            site={filters.site}
            role={filters.role}
            onChange={(values) => setFilters((prev) => ({ ...prev, ...values }))}
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <DeviceTable
            devices={devices}
            onEdit={openEditDialog}
            onDelete={openDeleteDialog}
            onOpenTerminal={(device) => setTerminalDevice(device)}
          />
        </CardContent>
      </Card>

      <div className="text-sm text-muted-foreground">Total devices: {totalDevices}</div>

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
    </div>
  )
}


