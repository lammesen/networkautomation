import { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import { AppSidebar } from './app-sidebar'
import { Separator } from '@/components/ui/separator'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb'
import { CommandPalette } from '@/components/CommandPalette'
import { DeviceTerminalDialog } from '@/features/devices/components/DeviceTerminalDialog'
import type { Device } from '@/types/device'

const routeLabels: Record<string, string> = {
  devices: 'Devices',
  jobs: 'Jobs',
  commands: 'Commands',
  compliance: 'Compliance',
  admin: 'Administration',
  credentials: 'Credentials',
  users: 'Users',
  customers: 'Customers',
}

export default function DashboardLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const clearAuth = useAuthStore((s) => s.clearAuth)
  const [terminalDevice, setTerminalDevice] = useState<Device | null>(null)

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  // Generate breadcrumb items from current path
  const pathSegments = location.pathname.split('/').filter(Boolean)
  const breadcrumbItems = pathSegments.map((segment, index) => {
    const path = '/' + pathSegments.slice(0, index + 1).join('/')
    const label = routeLabels[segment] || segment
    const isLast = index === pathSegments.length - 1
    return { path, label, isLast }
  })

  return (
    <SidebarProvider>
      <AppSidebar onLogout={handleLogout} />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbItems.map((item, index) => (
                <BreadcrumbItem key={item.path}>
                  {index > 0 && <BreadcrumbSeparator />}
                  {item.isLast ? (
                    <BreadcrumbPage>{item.label}</BreadcrumbPage>
                  ) : (
                    <BreadcrumbLink href={item.path}>{item.label}</BreadcrumbLink>
                  )}
                </BreadcrumbItem>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
          <div className="ml-auto flex items-center gap-2">
            <kbd className="hidden sm:inline-flex h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium text-muted-foreground">
              <span className="text-xs">⌘</span>K
            </kbd>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </SidebarInset>

      {/* Global command palette */}
      <CommandPalette onOpenTerminal={(device) => setTerminalDevice(device)} />

      {/* Terminal dialog opened from command palette */}
      <DeviceTerminalDialog
        open={Boolean(terminalDevice)}
        device={terminalDevice}
        onClose={() => setTerminalDevice(null)}
      />
    </SidebarProvider>
  )
}
