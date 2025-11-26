import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { useState } from 'react'
import { useAuthStore, selectCanModify } from '@/store/authStore'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { toast } from 'sonner'
import { Plus } from 'lucide-react'
import { CreateUserDialog } from './CreateUserDialog'

interface Customer {
  id: number
  name: string
}

interface User {
  id: number
  username: string
  role: string
  is_active: boolean
  customers: Customer[]
}

export function UsersTab() {
  const [filter, setFilter] = useState<'all' | 'pending'>('all')
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [isCustomerModalOpen, setIsCustomerModalOpen] = useState(false)
  const [selectedCustomerToAdd, setSelectedCustomerToAdd] = useState<string>("")
  const [isCreateUserOpen, setIsCreateUserOpen] = useState(false)
  
  // Confirm dialog state
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [confirmAction, setConfirmAction] = useState<{ type: 'toggle_status' | 'remove_customer'; user: User; customerId?: number } | null>(null)
  
  const queryClient = useQueryClient()
  const currentUser = useAuthStore((state) => state.user)
  const canModify = useAuthStore(selectCanModify)

  const { data: users, isLoading: isLoadingUsers, error: usersError } = useQuery({
    queryKey: ['users', filter],
    queryFn: () => apiClient.getUsers(filter === 'pending' ? { active: false } : undefined),
  })

  const { data: allCustomers } = useQuery({
    queryKey: ['customers'],
    queryFn: () => apiClient.getCustomers(),
    enabled: currentUser?.role === 'admin' && isCustomerModalOpen, 
  })

  const updateUserMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { role?: string; is_active?: boolean } }) =>
      apiClient.updateUser(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('User updated')
    },
    onError: () => {
      toast.error('Failed to update user')
    },
  })

  const addUserToCustomerMutation = useMutation({
    mutationFn: ({ customerId, userId }: { customerId: number; userId: number }) =>
      apiClient.addUserToCustomer(customerId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      setSelectedCustomerToAdd("")
      toast.success('Customer added')
    },
    onError: () => {
      toast.error('Failed to add customer')
    },
  })

  const removeUserFromCustomerMutation = useMutation({
    mutationFn: ({ customerId, userId }: { customerId: number; userId: number }) =>
      apiClient.removeUserFromCustomer(customerId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success('Customer removed')
    },
    onError: () => {
      toast.error('Failed to remove customer')
    },
  })

  if (isLoadingUsers) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (usersError) {
    return <div className="text-destructive p-4">Error loading users</div>
  }

  const handleRoleChange = (user: User, newRole: string) => {
    updateUserMutation.mutate({ id: user.id, data: { role: newRole } })
  }

  const handleToggleStatus = (user: User) => {
    if (currentUser?.id === user.id && currentUser.role === 'admin' && user.is_active) {
      toast.error("Admins cannot deactivate their own account.")
      return
    }

    setConfirmAction({ type: 'toggle_status', user })
    setConfirmDialogOpen(true)
  }

  const openCustomerModal = (user: User) => {
    setSelectedUser(user)
    setIsCustomerModalOpen(true)
  }

  const handleAddCustomer = () => {
    if (selectedUser && selectedCustomerToAdd) {
      addUserToCustomerMutation.mutate({ customerId: Number(selectedCustomerToAdd), userId: selectedUser.id })
    }
  }

  const handleRemoveCustomer = (customerId: number) => {
    if (selectedUser) {
      setConfirmAction({ type: 'remove_customer', user: selectedUser, customerId })
      setConfirmDialogOpen(true)
    }
  }

  const handleConfirmAction = () => {
    if (!confirmAction) return
    
    if (confirmAction.type === 'toggle_status') {
      updateUserMutation.mutate({ id: confirmAction.user.id, data: { is_active: !confirmAction.user.is_active } })
    } else if (confirmAction.type === 'remove_customer' && confirmAction.customerId) {
      removeUserFromCustomerMutation.mutate({ customerId: confirmAction.customerId, userId: confirmAction.user.id })
    }
    
    setConfirmDialogOpen(false)
    setConfirmAction(null)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Manage user accounts, roles, and customer assignments.
        </p>
        <div className="flex items-center gap-2">
          <Select value={filter} onValueChange={(val) => setFilter(val as 'all' | 'pending')}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Filter Users" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Users</SelectItem>
              <SelectItem value="pending">Pending Approval</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={() => setIsCreateUserOpen(true)} disabled={!canModify} title={!canModify ? 'Viewers cannot add users' : undefined}>
            <Plus className="mr-2 h-4 w-4" />
            Add User
          </Button>
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>Username</TableHead>
              <TableHead>Role</TableHead>
              <TableHead>Customers</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users && users.length > 0 ? (
              users.map((user: User) => {
                const isCurrentUserAdminAndActive = 
                  currentUser?.id === user.id && 
                  currentUser.role === 'admin' && 
                  user.is_active

                return (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">#{user.id}</TableCell>
                    <TableCell>{user.username}</TableCell>
                    <TableCell>
                      <Select
                        value={user.role}
                        onValueChange={(val) => handleRoleChange(user, val)}
                        disabled={currentUser?.id === user.id || !canModify}
                      >
                        <SelectTrigger className="w-[130px] h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="viewer">Viewer</SelectItem>
                          <SelectItem value="operator">Operator</SelectItem>
                          <SelectItem value="admin">Admin</SelectItem>
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell>
                       <div className="flex items-center gap-2">
                          <span className="text-sm text-muted-foreground">
                            {user.customers?.length || 0} assigned
                          </span>
                          <Button 
                            variant="outline" 
                            size="sm" 
                            className="h-7 text-xs"
                            onClick={() => openCustomerModal(user)}
                            disabled={!canModify}
                          >
                            Manage
                          </Button>
                       </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.is_active ? "default" : "destructive"}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant={user.is_active ? "destructive" : "default"}
                        size="sm"
                        onClick={() => handleToggleStatus(user)}
                        disabled={!!isCurrentUserAdminAndActive || !canModify}
                        className="h-8"
                      >
                        {user.is_active ? 'Deactivate' : 'Activate'}
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })
            ) : (
              <TableRow>
                <TableCell colSpan={6} className="text-center h-24 text-muted-foreground">
                  No users found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Customer Management Modal */}
      <Dialog open={isCustomerModalOpen} onOpenChange={setIsCustomerModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Manage Customers</DialogTitle>
            <DialogDescription>
               Assign or remove customers for user <strong>{selectedUser?.username}</strong>.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            <div className="space-y-2">
              <h3 className="text-sm font-medium">Add Customer</h3>
              <div className="flex gap-2">
                <Select value={selectedCustomerToAdd} onValueChange={setSelectedCustomerToAdd}>
                    <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select a customer..." />
                    </SelectTrigger>
                    <SelectContent>
                        {allCustomers?.filter((c: Customer) => !selectedUser?.customers?.some(uc => uc.id === c.id)).map((c: Customer) => (
                            <SelectItem key={c.id} value={c.id.toString()}>{c.name}</SelectItem>
                        ))}
                        {allCustomers?.filter((c: Customer) => !selectedUser?.customers?.some(uc => uc.id === c.id)).length === 0 && (
                            <div className="p-2 text-xs text-muted-foreground text-center">No more customers to add</div>
                        )}
                    </SelectContent>
                </Select>
                <Button 
                  onClick={handleAddCustomer}
                  disabled={!selectedCustomerToAdd || addUserToCustomerMutation.isPending}
                >
                  Add
                </Button>
              </div>
            </div>

            <div className="space-y-2">
              <h3 className="text-sm font-medium">Assigned Customers</h3>
              <div className="border rounded-md max-h-[200px] overflow-y-auto">
                {selectedUser?.customers && selectedUser.customers.length > 0 ? (
                    <Table>
                        <TableBody>
                        {selectedUser.customers.map(customer => (
                            <TableRow key={customer.id}>
                            <TableCell className="py-2">{customer.name}</TableCell>
                            <TableCell className="py-2 text-right">
                                <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                onClick={() => handleRemoveCustomer(customer.id)}
                                >
                                Remove
                                </Button>
                            </TableCell>
                            </TableRow>
                        ))}
                        </TableBody>
                    </Table>
                ) : (
                    <div className="p-4 text-center text-sm text-muted-foreground italic">No customers assigned.</div>
                )}
              </div>
            </div>
          </div>
          
          <DialogFooter>
              <Button variant="secondary" onClick={() => setIsCustomerModalOpen(false)}>
                Close
              </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Confirm Action Dialog */}
      <AlertDialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {confirmAction?.type === 'toggle_status' 
                ? `${confirmAction.user.is_active ? 'Deactivate' : 'Activate'} User`
                : 'Remove Customer Access'}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {confirmAction?.type === 'toggle_status'
                ? `Are you sure you want to ${confirmAction.user.is_active ? 'deactivate' : 'activate'} user ${confirmAction.user.username}?`
                : 'Are you sure you want to remove access to this customer?'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setConfirmAction(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleConfirmAction}>
              {confirmAction?.type === 'toggle_status'
                ? (confirmAction.user.is_active ? 'Deactivate' : 'Activate')
                : 'Remove'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Create User Dialog */}
      <CreateUserDialog open={isCreateUserOpen} onOpenChange={setIsCreateUserOpen} />
    </div>
  )
}
