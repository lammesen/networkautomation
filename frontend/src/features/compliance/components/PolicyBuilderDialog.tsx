import { useState, useMemo, useCallback } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Plus,
  Trash2,
  Copy,
  FileCode,
  Wand2,
  ListChecks,
  Target,
  Layers,
  Check,
  AlertCircle,
} from 'lucide-react'
import { toast } from 'sonner'
import type { CompliancePolicyCreate } from '@/types'

// NAPALM getters that can be used for compliance checks
const NAPALM_GETTERS = [
  { value: 'get_facts', label: 'Device Facts', description: 'Hostname, vendor, model, OS version, uptime' },
  { value: 'get_interfaces', label: 'Interfaces', description: 'Interface status, speed, MTU, MAC address' },
  { value: 'get_interfaces_ip', label: 'Interface IPs', description: 'IP addresses assigned to interfaces' },
  { value: 'get_lldp_neighbors', label: 'LLDP Neighbors', description: 'Connected neighbor devices via LLDP' },
  { value: 'get_bgp_neighbors', label: 'BGP Neighbors', description: 'BGP peer status and prefixes' },
  { value: 'get_ntp_servers', label: 'NTP Servers', description: 'Configured NTP server addresses' },
  { value: 'get_ntp_peers', label: 'NTP Peers', description: 'NTP peer associations and status' },
  { value: 'get_snmp_information', label: 'SNMP Info', description: 'SNMP community strings and contact info' },
  { value: 'get_users', label: 'Users', description: 'Local user accounts configured' },
  { value: 'get_vlans', label: 'VLANs', description: 'VLAN IDs and names' },
  { value: 'get_arp_table', label: 'ARP Table', description: 'ARP entries' },
  { value: 'get_mac_address_table', label: 'MAC Table', description: 'MAC address table entries' },
  { value: 'get_route_to', label: 'Routes', description: 'Routing table entries' },
] as const

// Common operators for compliance checks
const OPERATORS = [
  { value: 'equals', label: 'Equals (==)', description: 'Exact match' },
  { value: 'contains', label: 'Contains', description: 'Value includes text' },
  { value: 'starts_with', label: 'Starts With', description: 'Value begins with text' },
  { value: 'ends_with', label: 'Ends With', description: 'Value ends with text' },
  { value: 'gte', label: '>= (greater or equal)', description: 'Numeric comparison' },
  { value: 'lte', label: '<= (less or equal)', description: 'Numeric comparison' },
  { value: 'regex', label: 'Regex Match', description: 'Regular expression' },
  { value: 'present', label: 'Is Present', description: 'Field exists' },
  { value: 'absent', label: 'Is Absent', description: 'Field does not exist' },
] as const

// Pre-built policy templates
const POLICY_TEMPLATES = [
  {
    id: 'ntp-check',
    name: 'NTP Server Configured',
    description: 'Verify specific NTP servers are configured',
    getter: 'get_ntp_servers',
    yaml: `---
- get_ntp_servers:
    192.168.1.100:
      _mode: strict`,
  },
  {
    id: 'os-version',
    name: 'Minimum OS Version',
    description: 'Check devices are running minimum OS version',
    getter: 'get_facts',
    yaml: `---
- get_facts:
    os_version: "15.0"`,
  },
  {
    id: 'interface-up',
    name: 'Interface Status Check',
    description: 'Verify critical interfaces are up',
    getter: 'get_interfaces',
    yaml: `---
- get_interfaces:
    GigabitEthernet0/0:
      is_up: true
      is_enabled: true`,
  },
  {
    id: 'bgp-established',
    name: 'BGP Session Established',
    description: 'Check BGP neighbors are established',
    getter: 'get_bgp_neighbors',
    yaml: `---
- get_bgp_neighbors:
    global:
      peers:
        10.0.0.1:
          is_up: true
          is_enabled: true`,
  },
  {
    id: 'hostname-pattern',
    name: 'Hostname Convention',
    description: 'Verify hostname follows naming convention',
    getter: 'get_facts',
    yaml: `---
- get_facts:
    hostname: "^[a-z]{2,4}-[a-z]{2,4}-\\d{2}$"`,
  },
  {
    id: 'snmp-community',
    name: 'SNMP Community Check',
    description: 'Verify correct SNMP community strings',
    getter: 'get_snmp_information',
    yaml: `---
- get_snmp_information:
    community:
      public:
        _mode: absent`,
  },
  {
    id: 'vlan-exists',
    name: 'Required VLANs Present',
    description: 'Ensure required VLANs are configured',
    getter: 'get_vlans',
    yaml: `---
- get_vlans:
    100:
      name: "Management"
    200:
      name: "Users"`,
  },
] as const

interface Check {
  id: string
  field: string
  operator: string
  value: string
}

interface PolicyBuilderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: CompliancePolicyCreate) => void
  isPending?: boolean
  error?: string
}

export function PolicyBuilderDialog({
  open,
  onOpenChange,
  onSubmit,
  isPending,
  error,
}: PolicyBuilderDialogProps) {
  const [activeTab, setActiveTab] = useState('basics')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [selectedGetter, setSelectedGetter] = useState('')
  const [checks, setChecks] = useState<Check[]>([])
  const [manualYaml, setManualYaml] = useState('')
  const [useManualYaml, setUseManualYaml] = useState(false)
  const [scopeVendor, setScopeVendor] = useState('')
  const [scopePlatform, setScopePlatform] = useState('')
  const [scopeSite, setScopeSite] = useState('')

  // Generate YAML from visual builder
  const generatedYaml = useMemo(() => {
    if (!selectedGetter || checks.length === 0) return ''

    const checksObj: Record<string, unknown> = {}
    for (const check of checks) {
      if (!check.field) continue

      let checkValue: unknown = check.value
      
      // Handle special operators
      if (check.operator === 'present') {
        checkValue = { _mode: 'present' }
      } else if (check.operator === 'absent') {
        checkValue = { _mode: 'absent' }
      } else if (check.operator === 'gte' || check.operator === 'lte') {
        checkValue = { [`_${check.operator}`]: check.value }
      } else if (check.operator === 'contains') {
        checkValue = { _contains: check.value }
      } else if (check.operator === 'regex') {
        checkValue = check.value // NAPALM treats string as regex if it looks like one
      } else if (check.value === 'true') {
        checkValue = true
      } else if (check.value === 'false') {
        checkValue = false
      } else if (!isNaN(Number(check.value)) && check.value !== '') {
        checkValue = Number(check.value)
      }

      checksObj[check.field] = checkValue
    }

    const yaml = `---
- ${selectedGetter}:
${Object.entries(checksObj)
  .map(([key, val]) => {
    if (typeof val === 'object') {
      return `    ${key}:\n${Object.entries(val as Record<string, unknown>)
        .map(([k, v]) => `      ${k}: ${JSON.stringify(v)}`)
        .join('\n')}`
    }
    return `    ${key}: ${typeof val === 'string' ? `"${val}"` : val}`
  })
  .join('\n')}`

    return yaml
  }, [selectedGetter, checks])

  const finalYaml = useManualYaml ? manualYaml : generatedYaml

  const addCheck = useCallback(() => {
    setChecks((prev) => [
      ...prev,
      { id: crypto.randomUUID(), field: '', operator: 'equals', value: '' },
    ])
  }, [])

  const removeCheck = useCallback((id: string) => {
    setChecks((prev) => prev.filter((c) => c.id !== id))
  }, [])

  const updateCheck = useCallback((id: string, updates: Partial<Check>) => {
    setChecks((prev) => prev.map((c) => (c.id === id ? { ...c, ...updates } : c)))
  }, [])

  const applyTemplate = useCallback((template: (typeof POLICY_TEMPLATES)[number]) => {
    setName(template.name)
    setDescription(template.description)
    setManualYaml(template.yaml)
    setUseManualYaml(true)
    setActiveTab('yaml')
    toast.success(`Applied "${template.name}" template`)
  }, [])

  const copyYamlToClipboard = useCallback(() => {
    navigator.clipboard.writeText(finalYaml)
    toast.success('YAML copied to clipboard')
  }, [finalYaml])

  const handleSubmit = useCallback(() => {
    if (!name.trim()) {
      toast.error('Policy name is required')
      return
    }
    if (!finalYaml.trim()) {
      toast.error('Policy definition is required')
      return
    }

    const scopeJson: Record<string, unknown> = {}
    if (scopeVendor) scopeJson.vendor = scopeVendor
    if (scopePlatform) scopeJson.platform = scopePlatform
    if (scopeSite) scopeJson.site = scopeSite

    onSubmit({
      name: name.trim(),
      description: description.trim() || undefined,
      definition_yaml: finalYaml.trim(),
      scope_json: scopeJson,
    })
  }, [name, description, finalYaml, scopeVendor, scopePlatform, scopeSite, onSubmit])

  const resetForm = useCallback(() => {
    setName('')
    setDescription('')
    setSelectedGetter('')
    setChecks([])
    setManualYaml('')
    setUseManualYaml(false)
    setScopeVendor('')
    setScopePlatform('')
    setScopeSite('')
    setActiveTab('basics')
  }, [])

  // Reset form when dialog closes
  const handleOpenChange = useCallback(
    (newOpen: boolean) => {
      if (!newOpen) {
        resetForm()
      }
      onOpenChange(newOpen)
    },
    [onOpenChange, resetForm]
  )

  const isValid = name.trim() && finalYaml.trim()

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ListChecks className="h-5 w-5" />
            Create Compliance Policy
          </DialogTitle>
          <DialogDescription>
            Define validation rules to check device configuration and state compliance.
          </DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 overflow-hidden flex flex-col">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="basics" className="gap-2">
              <FileCode className="h-4 w-4" />
              Basics
            </TabsTrigger>
            <TabsTrigger value="builder" className="gap-2">
              <Wand2 className="h-4 w-4" />
              Builder
            </TabsTrigger>
            <TabsTrigger value="templates" className="gap-2">
              <Layers className="h-4 w-4" />
              Templates
            </TabsTrigger>
            <TabsTrigger value="yaml" className="gap-2">
              <Target className="h-4 w-4" />
              YAML
            </TabsTrigger>
          </TabsList>

          <ScrollArea className="flex-1 pr-4">
            <TabsContent value="basics" className="mt-4 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="policy-name">Policy Name *</Label>
                <Input
                  id="policy-name"
                  placeholder="e.g., ntp-server-check"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Use a descriptive name that identifies what this policy validates
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="policy-description">Description</Label>
                <Textarea
                  id="policy-description"
                  placeholder="Describe what this policy checks and why it's important..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                />
              </div>

              <Separator />

              <div className="space-y-4">
                <div>
                  <Label className="text-sm font-medium">Scope Filters (Optional)</Label>
                  <p className="text-xs text-muted-foreground mt-1">
                    Limit which devices this policy applies to
                  </p>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="scope-vendor" className="text-xs">Vendor</Label>
                    <Input
                      id="scope-vendor"
                      placeholder="e.g., Cisco"
                      value={scopeVendor}
                      onChange={(e) => setScopeVendor(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="scope-platform" className="text-xs">Platform</Label>
                    <Input
                      id="scope-platform"
                      placeholder="e.g., ios"
                      value={scopePlatform}
                      onChange={(e) => setScopePlatform(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="scope-site" className="text-xs">Site</Label>
                    <Input
                      id="scope-site"
                      placeholder="e.g., dc1"
                      value={scopeSite}
                      onChange={(e) => setScopeSite(e.target.value)}
                    />
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="builder" className="mt-4 space-y-4">
              <div className="space-y-2">
                <Label>Data Source (NAPALM Getter)</Label>
                <Select value={selectedGetter} onValueChange={setSelectedGetter}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select what data to validate..." />
                  </SelectTrigger>
                  <SelectContent>
                    {NAPALM_GETTERS.map((getter) => (
                      <SelectItem key={getter.value} value={getter.value}>
                        <div className="flex flex-col">
                          <span>{getter.label}</span>
                          <span className="text-xs text-muted-foreground">{getter.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {selectedGetter && (
                <Card>
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm">Validation Checks</CardTitle>
                      <Button size="sm" variant="outline" onClick={addCheck}>
                        <Plus className="h-4 w-4 mr-1" />
                        Add Check
                      </Button>
                    </div>
                    <CardDescription>
                      Define the fields and expected values to validate
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {checks.length === 0 ? (
                      <div className="text-center py-6 text-muted-foreground">
                        <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
                        <p className="text-sm">No checks defined yet</p>
                        <p className="text-xs">Click "Add Check" to define validation rules</p>
                      </div>
                    ) : (
                      checks.map((check, index) => (
                        <div key={check.id} className="flex items-start gap-2 p-3 border rounded-lg bg-muted/30">
                          <Badge variant="outline" className="mt-2 shrink-0">
                            {index + 1}
                          </Badge>
                          <div className="flex-1 grid grid-cols-3 gap-2">
                            <div className="space-y-1">
                              <Label className="text-xs">Field</Label>
                              <Input
                                placeholder="e.g., hostname, is_up"
                                value={check.field}
                                onChange={(e) => updateCheck(check.id, { field: e.target.value })}
                              />
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs">Operator</Label>
                              <Select
                                value={check.operator}
                                onValueChange={(v) => updateCheck(check.id, { operator: v })}
                              >
                                <SelectTrigger>
                                  <SelectValue />
                                </SelectTrigger>
                                <SelectContent>
                                  {OPERATORS.map((op) => (
                                    <SelectItem key={op.value} value={op.value}>
                                      {op.label}
                                    </SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            </div>
                            <div className="space-y-1">
                              <Label className="text-xs">Expected Value</Label>
                              <Input
                                placeholder="e.g., true, 15.0"
                                value={check.value}
                                onChange={(e) => updateCheck(check.id, { value: e.target.value })}
                                disabled={check.operator === 'present' || check.operator === 'absent'}
                              />
                            </div>
                          </div>
                          <Button
                            size="icon"
                            variant="ghost"
                            className="mt-6 text-muted-foreground hover:text-destructive"
                            onClick={() => removeCheck(check.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      ))
                    )}
                  </CardContent>
                </Card>
              )}

              {generatedYaml && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center gap-2">
                      <Check className="h-4 w-4 text-green-500" />
                      Generated YAML Preview
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <pre className="text-xs bg-muted p-3 rounded-md overflow-auto max-h-40 font-mono">
                      {generatedYaml}
                    </pre>
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            <TabsContent value="templates" className="mt-4">
              <div className="grid grid-cols-2 gap-3">
                {POLICY_TEMPLATES.map((template) => (
                  <Card
                    key={template.id}
                    className="cursor-pointer hover:border-primary transition-colors"
                    onClick={() => applyTemplate(template)}
                  >
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm">{template.name}</CardTitle>
                      <CardDescription className="text-xs">{template.description}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <Badge variant="secondary" className="text-xs">
                        {template.getter}
                      </Badge>
                    </CardContent>
                  </Card>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-4 text-center">
                Click a template to use it as a starting point. You can customize it in the YAML tab.
              </p>
            </TabsContent>

            <TabsContent value="yaml" className="mt-4 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Label>YAML Definition</Label>
                  {!useManualYaml && generatedYaml && (
                    <Badge variant="outline" className="text-xs">
                      Auto-generated from Builder
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      if (!useManualYaml && generatedYaml) {
                        setManualYaml(generatedYaml)
                      }
                      setUseManualYaml(!useManualYaml)
                    }}
                  >
                    {useManualYaml ? 'Use Builder Output' : 'Edit Manually'}
                  </Button>
                  {finalYaml && (
                    <Button size="sm" variant="ghost" onClick={copyYamlToClipboard}>
                      <Copy className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>

              <Textarea
                className="min-h-[300px] font-mono text-sm"
                placeholder={`---
- get_facts:
    hostname: "expected-hostname"
    os_version: "15.0"
- get_interfaces:
    GigabitEthernet0/0:
      is_up: true`}
                value={useManualYaml ? manualYaml : generatedYaml}
                onChange={(e) => {
                  setManualYaml(e.target.value)
                  if (!useManualYaml) setUseManualYaml(true)
                }}
                readOnly={!useManualYaml && !!generatedYaml}
              />

              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-xs">
                  YAML follows NAPALM validation format. Each getter returns specific data that can be validated.
                  Use <code className="bg-muted px-1 rounded">_mode: strict</code> for exact matches
                  or <code className="bg-muted px-1 rounded">_mode: absent</code> to ensure something is NOT configured.
                </AlertDescription>
              </Alert>
            </TabsContent>
          </ScrollArea>
        </Tabs>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={() => handleOpenChange(false)}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isValid || isPending}>
            {isPending ? 'Creating...' : 'Create Policy'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
