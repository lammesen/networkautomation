import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { CommandTargets } from '../types'
import { SUPPORTED_PLATFORMS } from '../types'

interface TargetFiltersProps {
  targets: CommandTargets
  onChange: (targets: CommandTargets) => void
}

export function TargetFilters({ targets, onChange }: TargetFiltersProps) {
  const updateTarget = (field: keyof CommandTargets, value: string) => {
    onChange({ ...targets, [field]: value })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Target Devices</CardTitle>
        <CardDescription>
          Select filters to scope devices. Choose a platform to enable autocomplete (Tab to accept).
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="space-y-2">
            <Label htmlFor="site">Site</Label>
            <Input
              id="site"
              value={targets.site}
              onChange={(e) => updateTarget('site', e.target.value)}
              placeholder="e.g., dc1"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="role">Role</Label>
            <Input
              id="role"
              value={targets.role}
              onChange={(e) => updateTarget('role', e.target.value)}
              placeholder="e.g., edge"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="vendor">Vendor</Label>
            <Input
              id="vendor"
              value={targets.vendor}
              onChange={(e) => updateTarget('vendor', e.target.value)}
              placeholder="e.g., cisco"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="platform">Platform</Label>
            <Select
              value={targets.platform}
              onValueChange={(value) => updateTarget('platform', value)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select Platform" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unknown">Select Platform</SelectItem>
                {SUPPORTED_PLATFORMS.map((p) => (
                  <SelectItem key={p} value={p}>
                    {p.toUpperCase()}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
