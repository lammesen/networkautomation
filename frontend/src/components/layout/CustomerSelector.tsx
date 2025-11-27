import { Building2, Check, ChevronsUpDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/store/authStore'
import { cn } from '@/lib/utils'

export function CustomerSelector() {
  const user = useAuthStore((s) => s.user)
  const activeCustomerId = useAuthStore((s) => s.activeCustomerId)
  const setActiveCustomer = useAuthStore((s) => s.setActiveCustomer)

  const customers = user?.customers || []

  // Don't show selector if user has no customers or only one
  if (customers.length <= 1) {
    return null
  }

  const activeCustomer = customers.find((c) => c.id === activeCustomerId)
  const displayName = activeCustomer?.name || 'All Customers'

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-between gap-2 px-2 h-9"
        >
          <div className="flex items-center gap-2 truncate">
            <Building2 className="h-4 w-4 shrink-0 text-muted-foreground" />
            <span className="truncate text-sm">{displayName}</span>
          </div>
          <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-56">
        <DropdownMenuLabel>Select Customer</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onClick={() => setActiveCustomer(null)}
          className="flex items-center justify-between"
        >
          <span>All Customers</span>
          {activeCustomerId === null && <Check className="h-4 w-4" />}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        {customers.map((customer) => (
          <DropdownMenuItem
            key={customer.id}
            onClick={() => setActiveCustomer(customer.id)}
            className="flex items-center justify-between"
          >
            <span className={cn(activeCustomerId === customer.id && 'font-medium')}>
              {customer.name}
            </span>
            {activeCustomerId === customer.id && <Check className="h-4 w-4" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
