import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Table, TableBody, TableHead, TableHeader, TableRow, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { StatusBadge } from '@/components/ui/status-badge'
import { EmptyTableRow } from '@/components/ui/empty-table-row'
import { LoadingSpinner } from '@/components/ui/query-state'
import { toast } from "sonner"
import { formatDateTime } from '@/lib/formatters'
import type { CompliancePolicy, CompliancePolicyCreate, ComplianceResult } from '@/types'

export default function CompliancePage() {
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false)
  const [newPolicy, setNewPolicy] = useState({ name: '', description: '', definition_yaml: '' })
  const [error, setError] = useState('')
  
  const queryClient = useQueryClient()

  const { data: policies, isLoading: isLoadingPolicies } = useQuery({
    queryKey: ['compliancePolicies'],
    queryFn: () => apiClient.getCompliancePolicies(),
  })

  const { data: results } = useQuery({
    queryKey: ['complianceResults'],
    queryFn: () => apiClient.getComplianceResults(),
  })

  const createPolicyMutation = useMutation({
    mutationFn: (data: CompliancePolicyCreate) => apiClient.createCompliancePolicy(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliancePolicies'] })
      setIsCreateModalOpen(false)
      setNewPolicy({ name: '', description: '', definition_yaml: '' })
      setError('')
      toast.success("Policy created")
    },
    onError: (err: Error & { data?: { detail?: string } }) => {
        const msg = err.data?.detail || err.message || 'Failed to create policy'
        setError(msg)
        toast.error(msg)
    },
  })

  const runComplianceMutation = useMutation({
    mutationFn: (policyId: number) => apiClient.runComplianceCheck(policyId),
    onSuccess: () => {
      toast.success('Compliance check started')
    },
    onError: (err: Error) => toast.error('Failed to start check: ' + err.message)
  })

  if (isLoadingPolicies) return <LoadingSpinner message="Loading compliance data..." />

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold tracking-tight">Compliance</h1>
        <Button onClick={() => setIsCreateModalOpen(true)}>
          Create Policy
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
            <CardHeader>
                <CardTitle>Policies</CardTitle>
            </CardHeader>
            <CardContent>
                <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Name</TableHead>
                            <TableHead>Actions</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {policies?.map((policy: CompliancePolicy) => (
                            <TableRow key={policy.id}>
                                <TableCell className="font-medium">{policy.name}</TableCell>
                                <TableCell>
                                    <Button size="sm" onClick={() => runComplianceMutation.mutate(policy.id)}>
                                        Run Check
                                    </Button>
                                </TableCell>
                            </TableRow>
                        ))}
                         {(!policies || policies.length === 0) && (
                            <EmptyTableRow colSpan={2} message="No policies found" />
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>

        <Card>
            <CardHeader>
                <CardTitle>Recent Results</CardTitle>
            </CardHeader>
            <CardContent>
                 <Table>
                    <TableHeader>
                        <TableRow>
                            <TableHead>Device</TableHead>
                            <TableHead>Policy</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Time</TableHead>
                        </TableRow>
                    </TableHeader>
                    <TableBody>
                        {results?.map((res: ComplianceResult) => (
                            <TableRow key={res.id}>
                                <TableCell>{res.device_id}</TableCell> 
                                <TableCell>{res.policy_id}</TableCell>
                                <TableCell>
                                    <StatusBadge status={res.status} />
                                </TableCell>
                                <TableCell>{formatDateTime(res.ts)}</TableCell>
                            </TableRow>
                        ))}
                        {(!results || results.length === 0) && (
                            <EmptyTableRow colSpan={4} message="No results found" />
                        )}
                    </TableBody>
                </Table>
            </CardContent>
        </Card>
      </div>

      <Dialog open={isCreateModalOpen} onOpenChange={setIsCreateModalOpen}>
        <DialogContent>
            <DialogHeader>
                <DialogTitle>Create Compliance Policy</DialogTitle>
            </DialogHeader>
            <form onSubmit={(e) => {
                e.preventDefault()
                createPolicyMutation.mutate({
                  name: newPolicy.name,
                  definition_yaml: newPolicy.definition_yaml,
                  scope_json: {},
                  description: newPolicy.description || undefined,
                })
            }} className="space-y-4">
                <div className="space-y-2">
                    <Label htmlFor="name">Name</Label>
                    <Input 
                        id="name" 
                        required 
                        value={newPolicy.name}
                        onChange={e => setNewPolicy({...newPolicy, name: e.target.value})}
                    />
                </div>
                 <div className="space-y-2">
                    <Label htmlFor="desc">Description</Label>
                    <Input 
                        id="desc" 
                        value={newPolicy.description}
                        onChange={e => setNewPolicy({...newPolicy, description: e.target.value})}
                    />
                </div>
                 <div className="space-y-2">
                    <Label htmlFor="def">Definition (YAML)</Label>
                    <Textarea 
                        id="def" 
                        required 
                        className="font-mono"
                        placeholder="getter: get_facts"
                        value={newPolicy.definition_yaml}
                        onChange={e => setNewPolicy({...newPolicy, definition_yaml: e.target.value})}
                    />
                </div>

                {error && (
                    <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
                )}

                <DialogFooter>
                    <Button type="submit" disabled={createPolicyMutation.isPending}>Create</Button>
                </DialogFooter>
            </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
