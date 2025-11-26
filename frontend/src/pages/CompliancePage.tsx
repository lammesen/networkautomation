import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Table, TableBody, TableHead, TableHeader, TableRow, TableCell } from '@/components/ui/table'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusBadge } from '@/components/ui/status-badge'
import { PageHeader } from '@/components/layout/page-header'
import { toast } from "sonner"
import { formatDateTime } from '@/lib/formatters'
import { Plus, Play, ShieldCheck, FileCheck } from 'lucide-react'
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

  if (isLoadingPolicies) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Compliance"
          description="Define and run compliance policies against your network devices"
        />
        <div className="grid gap-6 md:grid-cols-2">
          <Skeleton className="h-64 w-full" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Compliance"
        description="Define and run compliance policies against your network devices"
        actions={
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Policy
          </Button>
        }
      />

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-muted-foreground" />
              <div>
                <CardTitle>Policies</CardTitle>
                <CardDescription>
                  {policies?.length || 0} compliance {policies?.length === 1 ? 'policy' : 'policies'} defined
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead className="w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {policies?.map((policy: CompliancePolicy) => (
                  <TableRow key={policy.id}>
                    <TableCell>
                      <div className="font-medium">{policy.name}</div>
                      {policy.description && (
                        <div className="text-xs text-muted-foreground">{policy.description}</div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => runComplianceMutation.mutate(policy.id)}
                        disabled={runComplianceMutation.isPending}
                      >
                        <Play className="mr-1 h-3 w-3" />
                        Run
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {(!policies || policies.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={2} className="h-24 text-center text-muted-foreground">
                      No policies defined yet
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FileCheck className="h-5 w-5 text-muted-foreground" />
              <div>
                <CardTitle>Recent Results</CardTitle>
                <CardDescription>
                  Latest compliance check results
                </CardDescription>
              </div>
            </div>
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
                    <TableCell className="font-medium">{res.device_id}</TableCell> 
                    <TableCell>{res.policy_id}</TableCell>
                    <TableCell>
                      <StatusBadge status={res.status} />
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDateTime(res.ts)}
                    </TableCell>
                  </TableRow>
                ))}
                {(!results || results.length === 0) && (
                  <TableRow>
                    <TableCell colSpan={4} className="h-24 text-center text-muted-foreground">
                      No results yet
                    </TableCell>
                  </TableRow>
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
            <DialogDescription>
              Define a new compliance policy using YAML syntax.
            </DialogDescription>
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
                placeholder="e.g. ntp-config-check"
                value={newPolicy.name}
                onChange={e => setNewPolicy({...newPolicy, name: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="desc">Description</Label>
              <Input 
                id="desc" 
                placeholder="Optional description..."
                value={newPolicy.description}
                onChange={e => setNewPolicy({...newPolicy, description: e.target.value})}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="def">Definition (YAML)</Label>
              <Textarea 
                id="def" 
                required 
                className="font-mono min-h-[120px]"
                placeholder="getter: get_facts&#10;checks:&#10;  - field: os_version&#10;    operator: gte&#10;    value: '15.0'"
                value={newPolicy.definition_yaml}
                onChange={e => setNewPolicy({...newPolicy, definition_yaml: e.target.value})}
              />
              <p className="text-xs text-muted-foreground">
                Define the getter and checks for this compliance policy
              </p>
            </div>

            {error && (
              <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setIsCreateModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={createPolicyMutation.isPending}>
                {createPolicyMutation.isPending ? 'Creating...' : 'Create Policy'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
