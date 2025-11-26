import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '@/components/ui/alert-dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { Plus, Building2, Network } from 'lucide-react'
import { toast } from 'sonner'
import type { Customer, IPRange } from '@/types'

export function CustomersTab() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [isIPModalOpen, setIsIPModalOpen] = useState(false)
  
  // Confirm dialog state
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false)
  const [rangeToDelete, setRangeToDelete] = useState<IPRange | null>(null)
  
  // Form states
  const [newCustomerData, setNewCustomerData] = useState({ name: '', description: '' })
  const [newIPData, setNewIPData] = useState({ cidr: '', description: '' })
  const [error, setError] = useState('')

  const queryClient = useQueryClient()

  const { data: customers, isLoading } = useQuery({
    queryKey: ['customers'],
    queryFn: () => apiClient.getCustomers(),
  })

  const { data: ipRanges } = useQuery({
    queryKey: ['customerIPRanges', selectedCustomer?.id],
    queryFn: () => apiClient.getCustomerIPRanges(selectedCustomer!.id),
    enabled: !!selectedCustomer && isIPModalOpen,
  })

  const createCustomerMutation = useMutation({
    mutationFn: (data: { name: string; description?: string }) => apiClient.createCustomer(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customers'] })
      setIsCreateModalOpen(false)
      setNewCustomerData({ name: '', description: '' })
      setError('')
      toast.success('Customer created')
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || 'Failed to create customer')
    },
  })

  const createIPRangeMutation = useMutation({
    mutationFn: (data: { cidr: string; description?: string }) => 
      apiClient.createCustomerIPRange(selectedCustomer!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customerIPRanges', selectedCustomer?.id] })
      setNewIPData({ cidr: '', description: '' })
      setError('')
      toast.success('IP range added')
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || 'Failed to add IP range')
    },
  })

  const deleteIPRangeMutation = useMutation({
    mutationFn: (rangeId: number) => 
      apiClient.deleteCustomerIPRange(selectedCustomer!.id, rangeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customerIPRanges', selectedCustomer?.id] })
      toast.success('IP range deleted')
    },
    onError: () => {
      toast.error('Failed to delete IP range')
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Manage customer organizations and their assigned IP ranges.
        </p>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Customer
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Created At</TableHead>
              <TableHead>Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {customers?.map((customer: Customer) => (
              <TableRow key={customer.id}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{customer.name}</span>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {customer.description || '-'}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {new Date(customer.created_at).toLocaleDateString()}
                </TableCell>
                <TableCell>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedCustomer(customer)
                      setIsIPModalOpen(true)
                    }}
                  >
                    <Network className="mr-2 h-4 w-4" />
                    IP Ranges
                  </Button>
                </TableCell>
              </TableRow>
            ))}
            {(!customers || customers.length === 0) && (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground h-24">
                  No customers found
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create Customer Modal */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Customer</DialogTitle>
            <DialogDescription>Add a new customer organization to the system.</DialogDescription>
          </DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault()
            createCustomerMutation.mutate(newCustomerData)
          }} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                required
                placeholder="Acme Corporation"
                value={newCustomerData.name}
                onChange={e => setNewCustomerData({...newCustomerData, name: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Optional description..."
                value={newCustomerData.description}
                onChange={e => setNewCustomerData({...newCustomerData, description: e.target.value})}
              />
            </div>
            
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsCreateModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createCustomerMutation.isPending}>
                {createCustomerMutation.isPending ? 'Creating...' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Manage IP Ranges Modal */}
      <Dialog open={isIPModalOpen} onOpenChange={(open) => {
        if (!open) {
          setIsIPModalOpen(false)
          setError('')
        }
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>IP Ranges for {selectedCustomer?.name}</DialogTitle>
            <DialogDescription>Manage CIDR blocks assigned to this customer.</DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* List Ranges */}
            <div className="rounded-md border">
              {ipRanges && ipRanges.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>CIDR</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="w-[100px]">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {ipRanges.map((range: IPRange) => (
                      <TableRow key={range.id}>
                        <TableCell>
                          <code className="text-sm bg-muted px-2 py-0.5 rounded">
                            {range.cidr}
                          </code>
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {range.description || '-'}
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="destructive"
                            size="sm"
                            onClick={() => {
                              setRangeToDelete(range)
                              setConfirmDialogOpen(true)
                            }}
                          >
                            Delete
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="p-4 text-center text-muted-foreground">
                  No IP ranges configured.
                </div>
              )}
            </div>

            {/* Add Range Form */}
            <div className="space-y-4 border-t pt-4">
              <h3 className="text-sm font-medium">Add New Range</h3>
              <form onSubmit={(e) => {
                e.preventDefault()
                createIPRangeMutation.mutate(newIPData)
              }} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="cidr">CIDR</Label>
                    <Input
                      id="cidr"
                      required
                      placeholder="10.0.0.0/24"
                      value={newIPData.cidr}
                      onChange={e => setNewIPData({...newIPData, cidr: e.target.value})}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="range-desc">Description</Label>
                    <Input
                      id="range-desc"
                      placeholder="Office Network"
                      value={newIPData.description}
                      onChange={e => setNewIPData({...newIPData, description: e.target.value})}
                    />
                  </div>
                </div>

                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}

                <div className="flex justify-end">
                  <Button type="submit" disabled={createIPRangeMutation.isPending}>
                    {createIPRangeMutation.isPending ? 'Adding...' : 'Add Range'}
                  </Button>
                </div>
              </form>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Confirm Delete Dialog */}
      <AlertDialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete IP Range</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the IP range <strong>{rangeToDelete?.cidr}</strong>? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setRangeToDelete(null)}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (rangeToDelete) {
                  deleteIPRangeMutation.mutate(rangeToDelete.id)
                }
                setConfirmDialogOpen(false)
                setRangeToDelete(null)
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
