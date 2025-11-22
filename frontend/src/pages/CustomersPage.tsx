import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

interface Customer {
  id: number
  name: string
  description?: string
  created_at: string
}

interface IPRange {
  id: number
  cidr: string
  description?: string
  created_at: string
}

export default function CustomersPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [selectedCustomer, setSelectedCustomer] = useState<Customer | null>(null)
  const [isIPModalOpen, setIsIPModalOpen] = useState(false)
  
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
    },
    onError: (err: any) => setError(err.response?.data?.detail || 'Failed to create customer'),
  })

  const createIPRangeMutation = useMutation({
    mutationFn: (data: { cidr: string; description?: string }) => 
      apiClient.createCustomerIPRange(selectedCustomer!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customerIPRanges', selectedCustomer?.id] })
      setNewIPData({ cidr: '', description: '' })
      setError('')
    },
    onError: (err: any) => setError(err.response?.data?.detail || 'Failed to add IP range'),
  })

  const deleteIPRangeMutation = useMutation({
    mutationFn: (rangeId: number) => 
      apiClient.deleteCustomerIPRange(selectedCustomer!.id, rangeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customerIPRanges', selectedCustomer?.id] })
    },
  })

  if (isLoading) return <div>Loading customers...</div>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Customer Management</h1>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          Add Customer
        </Button>
      </div>

      <Card>
        <CardHeader>
            <CardTitle>Customers</CardTitle>
        </CardHeader>
        <CardContent>
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
                    <TableCell className="font-medium">{customer.name}</TableCell>
                    <TableCell>{customer.description || '-'}</TableCell>
                    <TableCell>{new Date(customer.created_at).toLocaleDateString()}</TableCell>
                    <TableCell>
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                        setSelectedCustomer(customer)
                        setIsIPModalOpen(true)
                        }}
                    >
                        Manage IP Ranges
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
        </CardContent>
      </Card>

      {/* Create Customer Modal */}
      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Customer</DialogTitle>
            <DialogDescription>Add a new customer to the system.</DialogDescription>
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
                value={newCustomerData.name}
                onChange={e => setNewCustomerData({...newCustomerData, name: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
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
          if (!open) setIsIPModalOpen(false);
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
                            <TableCell className="font-medium">{range.cidr}</TableCell>
                            <TableCell>{range.description}</TableCell>
                            <TableCell>
                                <Button
                                variant="destructive"
                                size="sm"
                                onClick={() => {
                                    if (confirm('Delete this IP range?')) {
                                    deleteIPRangeMutation.mutate(range.id)
                                    }
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
                    <div className="p-4 text-center text-muted-foreground">No IP ranges configured.</div>
                )}
                </div>

                {/* Add Range Form */}
                <div className="space-y-4 border-t pt-4">
                    <h3 className="text-lg font-medium">Add New Range</h3>
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
    </div>
  )
}