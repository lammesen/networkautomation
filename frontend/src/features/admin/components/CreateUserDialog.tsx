import { useState, useEffect } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { toast } from 'sonner'
import { Eye, EyeOff, UserPlus, Shield, Building2, Check, X } from 'lucide-react'
import type { Customer, AdminUserCreate } from '@/types'

interface CreateUserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface PasswordValidation {
  minLength: boolean
  hasUppercase: boolean
  hasLowercase: boolean
  hasNumber: boolean
}

const ROLE_DESCRIPTIONS = {
  viewer: 'Read-only access to assigned customers',
  operator: 'Can run commands and view configurations',
  admin: 'Full system access and user management',
}

export function CreateUserDialog({ open, onOpenChange }: CreateUserDialogProps) {
  const queryClient = useQueryClient()
  
  // Form state
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [role, setRole] = useState<'viewer' | 'operator' | 'admin'>('viewer')
  const [isActive, setIsActive] = useState(true)
  const [selectedCustomerIds, setSelectedCustomerIds] = useState<number[]>([])
  
  // UI state
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [step, setStep] = useState<'details' | 'customers'>('details')

  // Fetch customers for assignment
  const { data: customers } = useQuery({
    queryKey: ['customers'],
    queryFn: () => apiClient.getCustomers(),
    enabled: open,
  })

  // Password validation
  const passwordValidation: PasswordValidation = {
    minLength: password.length >= 8,
    hasUppercase: /[A-Z]/.test(password),
    hasLowercase: /[a-z]/.test(password),
    hasNumber: /\d/.test(password),
  }

  const isPasswordValid = Object.values(passwordValidation).every(Boolean)
  const passwordsMatch = password === confirmPassword && confirmPassword.length > 0

  // Username validation
  const usernameValid = /^[a-zA-Z][a-zA-Z0-9_-]*$/.test(username) && username.length >= 3

  // Reset form when dialog closes
  useEffect(() => {
    if (!open) {
      setUsername('')
      setPassword('')
      setConfirmPassword('')
      setRole('viewer')
      setIsActive(true)
      setSelectedCustomerIds([])
      setError('')
      setStep('details')
      setShowPassword(false)
      setShowConfirmPassword(false)
    }
  }, [open])

  const createUserMutation = useMutation({
    mutationFn: (data: AdminUserCreate) => apiClient.createUser(data),
    onSuccess: (user) => {
      queryClient.invalidateQueries({ queryKey: ['users'] })
      toast.success(`User "${user.username}" created successfully`)
      onOpenChange(false)
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setError(err.response?.data?.detail || err.message || 'Failed to create user')
    },
  })

  const handleSubmit = () => {
    setError('')

    if (!usernameValid) {
      setError('Username must start with a letter and contain only letters, numbers, underscores, or hyphens')
      return
    }

    if (!isPasswordValid) {
      setError('Password does not meet complexity requirements')
      return
    }

    if (!passwordsMatch) {
      setError('Passwords do not match')
      return
    }

    createUserMutation.mutate({
      username,
      password,
      role,
      is_active: isActive,
      customer_ids: selectedCustomerIds,
    })
  }

  const toggleCustomer = (customerId: number) => {
    setSelectedCustomerIds((prev) =>
      prev.includes(customerId)
        ? prev.filter((id) => id !== customerId)
        : [...prev, customerId]
    )
  }

  const canProceedToCustomers = usernameValid && isPasswordValid && passwordsMatch

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <UserPlus className="h-5 w-5" />
            Create New User
          </DialogTitle>
          <DialogDescription>
            {step === 'details' 
              ? 'Set up user credentials and role' 
              : 'Assign customers to this user'}
          </DialogDescription>
        </DialogHeader>

        {/* Step indicator */}
        <div className="flex items-center gap-2 mb-2">
          <div className={`flex items-center gap-1.5 text-sm ${step === 'details' ? 'text-primary font-medium' : 'text-muted-foreground'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step === 'details' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>1</div>
            Details
          </div>
          <Separator className="flex-1" />
          <div className={`flex items-center gap-1.5 text-sm ${step === 'customers' ? 'text-primary font-medium' : 'text-muted-foreground'}`}>
            <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step === 'customers' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>2</div>
            Customers
          </div>
        </div>

        {step === 'details' ? (
          <div className="space-y-4">
            {/* Username */}
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                placeholder="johndoe"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className={username && !usernameValid ? 'border-destructive' : ''}
              />
              {username && !usernameValid && (
                <p className="text-xs text-destructive">
                  Must start with a letter, 3+ characters, letters/numbers/underscores/hyphens only
                </p>
              )}
            </div>

            {/* Password */}
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pr-10"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              
              {/* Password requirements */}
              {password && (
                <div className="grid grid-cols-2 gap-1 text-xs">
                  <div className={`flex items-center gap-1 ${passwordValidation.minLength ? 'text-green-600' : 'text-muted-foreground'}`}>
                    {passwordValidation.minLength ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                    8+ characters
                  </div>
                  <div className={`flex items-center gap-1 ${passwordValidation.hasUppercase ? 'text-green-600' : 'text-muted-foreground'}`}>
                    {passwordValidation.hasUppercase ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                    Uppercase letter
                  </div>
                  <div className={`flex items-center gap-1 ${passwordValidation.hasLowercase ? 'text-green-600' : 'text-muted-foreground'}`}>
                    {passwordValidation.hasLowercase ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                    Lowercase letter
                  </div>
                  <div className={`flex items-center gap-1 ${passwordValidation.hasNumber ? 'text-green-600' : 'text-muted-foreground'}`}>
                    {passwordValidation.hasNumber ? <Check className="h-3 w-3" /> : <X className="h-3 w-3" />}
                    Number
                  </div>
                </div>
              )}
            </div>

            {/* Confirm Password */}
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password</Label>
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  placeholder="Confirm password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className={`pr-10 ${confirmPassword && !passwordsMatch ? 'border-destructive' : ''}`}
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 hover:bg-transparent"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                >
                  {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              {confirmPassword && !passwordsMatch && (
                <p className="text-xs text-destructive">Passwords do not match</p>
              )}
              {confirmPassword && passwordsMatch && (
                <p className="text-xs text-green-600 flex items-center gap-1">
                  <Check className="h-3 w-3" /> Passwords match
                </p>
              )}
            </div>

            {/* Role */}
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={role} onValueChange={(v) => setRole(v as typeof role)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="viewer">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-muted-foreground" />
                      Viewer
                    </div>
                  </SelectItem>
                  <SelectItem value="operator">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-blue-500" />
                      Operator
                    </div>
                  </SelectItem>
                  <SelectItem value="admin">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4 text-amber-500" />
                      Admin
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">{ROLE_DESCRIPTIONS[role]}</p>
            </div>

            {/* Active status */}
            <div className="flex items-center justify-between rounded-lg border p-3">
              <div className="space-y-0.5">
                <Label htmlFor="active">Account Active</Label>
                <p className="text-xs text-muted-foreground">
                  User can log in immediately if active
                </p>
              </div>
              <Switch
                id="active"
                checked={isActive}
                onCheckedChange={setIsActive}
              />
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Select customers this user can access
              </p>
              <Badge variant="secondary">
                {selectedCustomerIds.length} selected
              </Badge>
            </div>

            <ScrollArea className="h-[240px] rounded-md border">
              {customers && customers.length > 0 ? (
                <div className="p-2 space-y-1">
                  {customers.map((customer: Customer) => (
                    <div
                      key={customer.id}
                      className={`flex items-center gap-3 p-2 rounded-md cursor-pointer transition-colors ${
                        selectedCustomerIds.includes(customer.id)
                          ? 'bg-primary/10'
                          : 'hover:bg-muted'
                      }`}
                      onClick={() => toggleCustomer(customer.id)}
                    >
                      <Checkbox
                        checked={selectedCustomerIds.includes(customer.id)}
                        onCheckedChange={() => toggleCustomer(customer.id)}
                      />
                      <Building2 className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{customer.name}</p>
                        {customer.description && (
                          <p className="text-xs text-muted-foreground truncate">
                            {customer.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
                  No customers available
                </div>
              )}
            </ScrollArea>

            {role === 'admin' && (
              <Alert>
                <Shield className="h-4 w-4" />
                <AlertDescription>
                  Admin users have access to all customers regardless of selection.
                </AlertDescription>
              </Alert>
            )}
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <DialogFooter className="gap-2 sm:gap-0">
          {step === 'customers' && (
            <Button
              type="button"
              variant="outline"
              onClick={() => setStep('details')}
            >
              Back
            </Button>
          )}
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          {step === 'details' ? (
            <Button
              type="button"
              onClick={() => setStep('customers')}
              disabled={!canProceedToCustomers}
            >
              Next
            </Button>
          ) : (
            <Button
              type="button"
              onClick={handleSubmit}
              disabled={createUserMutation.isPending}
            >
              {createUserMutation.isPending ? 'Creating...' : 'Create User'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
