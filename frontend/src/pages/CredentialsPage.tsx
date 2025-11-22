import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function CredentialsPage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newCred, setNewCred] = useState({ name: '', username: '', password: '' })
  const [error, setError] = useState('')
  
  const queryClient = useQueryClient()

  const { data: credentials, isLoading } = useQuery({
    queryKey: ['credentials'],
    queryFn: () => apiClient.getCredentials(),
  })

  const createCredentialMutation = useMutation({
    mutationFn: (data: any) => apiClient.createCredential(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['credentials'] })
      setIsCreateModalOpen(false)
      setNewCred({ name: '', username: '', password: '' })
      setError('')
    },
    onError: (err: any) => setError(err.response?.data?.detail || 'Failed to create credential'),
  })

  if (isLoading) return <div>Loading credentials...</div>

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Credentials</h1>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          Add Credential
        </Button>
      </div>

      <Card>
        <CardHeader>
            <CardTitle>Manage Credentials</CardTitle>
        </CardHeader>
        <CardContent>
            <Table>
            <TableHeader>
                <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Username</TableHead>
                <TableHead>Created At</TableHead>
                </TableRow>
            </TableHeader>
            <TableBody>
                {credentials?.map((cred: any) => (
                <TableRow key={cred.id}>
                    <TableCell className="font-medium">{cred.name}</TableCell>
                    <TableCell>{cred.username}</TableCell>
                    <TableCell>{new Date(cred.created_at).toLocaleDateString()}</TableCell>
                </TableRow>
                ))}
                {(!credentials || credentials.length === 0) && (
                <TableRow>
                    <TableCell colSpan={3} className="text-center text-muted-foreground h-24">
                    No credentials found
                    </TableCell>
                </TableRow>
                )}
            </TableBody>
            </Table>
        </CardContent>
      </Card>

      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Credential</DialogTitle>
            <DialogDescription>Store new device credentials securely.</DialogDescription>
          </DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault()
            createCredentialMutation.mutate(newCred)
          }} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name (Alias)</Label>
              <Input
                id="name"
                required
                placeholder="e.g. Linux Test"
                value={newCred.name}
                onChange={e => setNewCred({...newCred, name: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                required
                value={newCred.username}
                onChange={e => setNewCred({...newCred, username: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={newCred.password}
                onChange={e => setNewCred({...newCred, password: e.target.value})}
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
              <Button type="submit" disabled={createCredentialMutation.isPending}>
                {createCredentialMutation.isPending ? 'Saving...' : 'Save'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}