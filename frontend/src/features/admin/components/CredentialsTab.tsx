import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient, ApiError } from '@/api/client'
import { Key, MoreHorizontal, Pencil, Trash2, Plus, Search, Server } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { toast } from 'sonner'
import type { Credential, CredentialCreate, CredentialUpdate } from '@/types'

type ModalMode = 'create' | 'edit' | null

interface CredentialFormData {
  name: string
  username: string
  password: string
  enable_password: string
}

const emptyFormData: CredentialFormData = {
  name: '',
  username: '',
  password: '',
  enable_password: '',
}

export function CredentialsTab() {
  const [modalMode, setModalMode] = useState<ModalMode>(null)
  const [selectedCredential, setSelectedCredential] = useState<Credential | null>(null)
  const [formData, setFormData] = useState<CredentialFormData>(emptyFormData)
  const [error, setError] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [credentialToDelete, setCredentialToDelete] = useState<Credential | null>(null)

  const queryClient = useQueryClient()

  // Fetch credentials
  const { data: credentials, isLoading: credentialsLoading } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => apiClient.getCredentials(),
  })

  // Fetch devices to compute usage count
  const { data: devicesData } = useQuery({
    queryKey: ['devices'],
    queryFn: () => apiClient.getDevices({ limit: 1000 }),
  })

  // Compute device count per credential
  const deviceCountByCredential = useMemo(() => {
    const counts: Record<number, number> = {}
    if (devicesData?.devices) {
      for (const device of devicesData.devices) {
        counts[device.credentials_ref] = (counts[device.credentials_ref] || 0) + 1
      }
    }
    return counts
  }, [devicesData])

  // Filter credentials by search query
  const filteredCredentials = useMemo(() => {
    if (!credentials) return []
    if (!searchQuery.trim()) return credentials
    const query = searchQuery.toLowerCase()
    return credentials.filter(
      (cred) =>
        cred.name.toLowerCase().includes(query) ||
        cred.username.toLowerCase().includes(query)
    )
  }, [credentials, searchQuery])

  // Create credential mutation
  const createMutation = useMutation({
    mutationFn: (data: CredentialCreate) => apiClient.createCredential(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
      closeModal()
      toast.success('Credential created')
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : 'Failed to create credential'
      setError(message)
    },
  })

  // Update credential mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: CredentialUpdate }) =>
      apiClient.updateCredential(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
      closeModal()
      toast.success('Credential updated')
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : 'Failed to update credential'
      setError(message)
    },
  })

  // Delete credential mutation
  const deleteMutation = useMutation({
    mutationFn: (id: number) => apiClient.deleteCredential(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
      setDeleteDialogOpen(false)
      setCredentialToDelete(null)
      toast.success('Credential deleted')
    },
    onError: (err: unknown) => {
      const message = err instanceof ApiError ? err.message : 'Failed to delete credential'
      toast.error(message)
      setDeleteDialogOpen(false)
      setCredentialToDelete(null)
    },
  })

  const openCreateModal = () => {
    setFormData(emptyFormData)
    setSelectedCredential(null)
    setError('')
    setModalMode('create')
  }

  const openEditModal = (credential: Credential) => {
    setFormData({
      name: credential.name,
      username: credential.username,
      password: '',
      enable_password: '',
    })
    setSelectedCredential(credential)
    setError('')
    setModalMode('edit')
  }

  const closeModal = () => {
    setModalMode(null)
    setSelectedCredential(null)
    setFormData(emptyFormData)
    setError('')
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (modalMode === 'create') {
      const payload: CredentialCreate = {
        name: formData.name,
        username: formData.username,
        password: formData.password,
      }
      if (formData.enable_password) {
        payload.enable_password = formData.enable_password
      }
      createMutation.mutate(payload)
    } else if (modalMode === 'edit' && selectedCredential) {
      const payload: CredentialUpdate = {}
      if (formData.name !== selectedCredential.name) payload.name = formData.name
      if (formData.username !== selectedCredential.username) payload.username = formData.username
      if (formData.password) payload.password = formData.password
      if (formData.enable_password) payload.enable_password = formData.enable_password

      // Only update if there are changes
      if (Object.keys(payload).length === 0) {
        closeModal()
        return
      }
      updateMutation.mutate({ id: selectedCredential.id, data: payload })
    }
  }

  const confirmDelete = (credential: Credential) => {
    setCredentialToDelete(credential)
    setDeleteDialogOpen(true)
  }

  const handleDelete = () => {
    if (credentialToDelete) {
      deleteMutation.mutate(credentialToDelete.id)
    }
  }

  const isSubmitting = createMutation.isPending || updateMutation.isPending

  if (credentialsLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  const totalCredentials = credentials?.length ?? 0
  const totalDevicesUsing = Object.values(deviceCountByCredential).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-4">
      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-4">
        <div className="flex items-center gap-3 p-3 rounded-lg border bg-card">
          <Key className="h-5 w-5 text-muted-foreground" />
          <div>
            <div className="text-2xl font-bold">{totalCredentials}</div>
            <div className="text-xs text-muted-foreground">Credentials</div>
          </div>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg border bg-card">
          <Server className="h-5 w-5 text-muted-foreground" />
          <div>
            <div className="text-2xl font-bold">{totalDevicesUsing}</div>
            <div className="text-xs text-muted-foreground">Devices Using</div>
          </div>
        </div>
        <div className="flex items-center gap-3 p-3 rounded-lg border bg-card">
          <div className="h-5 w-5 rounded-full bg-green-500/20 flex items-center justify-center">
            <div className="h-2 w-2 rounded-full bg-green-500" />
          </div>
          <div>
            <div className="text-sm font-medium text-green-600">Encrypted</div>
            <div className="text-xs text-muted-foreground">AES-256</div>
          </div>
        </div>
      </div>

      {/* Search and Add */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search credentials..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <Button onClick={openCreateModal}>
          <Plus className="mr-2 h-4 w-4" />
          Add Credential
        </Button>
      </div>

      {/* Credentials Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Username</TableHead>
              <TableHead>Devices</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-[70px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredCredentials.map((cred) => {
              const deviceCount = deviceCountByCredential[cred.id] || 0
              return (
                <TableRow key={cred.id}>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Key className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium">{cred.name}</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <code className="text-sm bg-muted px-2 py-0.5 rounded">
                      {cred.username}
                    </code>
                  </TableCell>
                  <TableCell>
                    <Badge variant={deviceCount > 0 ? 'default' : 'secondary'}>
                      {deviceCount} {deviceCount === 1 ? 'device' : 'devices'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(cred.created_at).toLocaleDateString(undefined, {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <MoreHorizontal className="h-4 w-4" />
                          <span className="sr-only">Open menu</span>
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEditModal(cred)}>
                          <Pencil className="mr-2 h-4 w-4" />
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => confirmDelete(cred)}
                          className="text-destructive focus:text-destructive"
                          disabled={deviceCount > 0}
                        >
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                          {deviceCount > 0 && (
                            <span className="ml-2 text-xs">(in use)</span>
                          )}
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              )
            })}
            {filteredCredentials.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground h-24">
                  {searchQuery ? 'No credentials match your search' : 'No credentials found'}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create/Edit Modal */}
      <Dialog open={modalMode !== null} onOpenChange={(open) => !open && closeModal()}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>
              {modalMode === 'create' ? 'Add Credential' : 'Edit Credential'}
            </DialogTitle>
            <DialogDescription>
              {modalMode === 'create'
                ? 'Store new device credentials securely. Passwords are encrypted at rest.'
                : 'Update credential details. Leave password blank to keep unchanged.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                required
                placeholder="e.g. cisco-core-creds"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                A unique identifier for this credential set
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                required
                placeholder="admin"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">
                Password
                {modalMode === 'edit' && (
                  <span className="text-muted-foreground font-normal ml-1">(leave blank to keep)</span>
                )}
              </Label>
              <Input
                id="password"
                type="password"
                required={modalMode === 'create'}
                placeholder={modalMode === 'edit' ? '••••••••' : ''}
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="enable_password">
                Enable Password
                <span className="text-muted-foreground font-normal ml-1">(optional)</span>
              </Label>
              <Input
                id="enable_password"
                type="password"
                placeholder="For privileged mode access"
                value={formData.enable_password}
                onChange={(e) => setFormData({ ...formData, enable_password: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                Required for Cisco IOS and similar platforms
              </p>
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={closeModal}>
                Cancel
              </Button>
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting
                  ? 'Saving...'
                  : modalMode === 'create'
                    ? 'Create Credential'
                    : 'Save Changes'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Credential</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete{' '}
              <span className="font-semibold">{credentialToDelete?.name}</span>? This action
              cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
