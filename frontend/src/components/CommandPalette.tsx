import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from '@/components/ui/command'
import {
  Server,
  Terminal,
  Briefcase,
  Shield,
  Moon,
  Sun,
  Monitor,
  Search,
  Play,
  Users,
  Key,
  Building2,
} from 'lucide-react'
import { apiClient } from '@/api/client'
import { useUIStore } from '@/store/uiStore'
import type { Device } from '@/types/device'

interface CommandPaletteProps {
  onOpenTerminal?: (device: Device) => void
}

export function CommandPalette({ onOpenTerminal }: CommandPaletteProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const { theme, setTheme } = useUIStore()

  // Fetch devices for search
  const { data: devicesData } = useQuery({
    queryKey: ['devices-palette'],
    queryFn: () => apiClient.getDevices({ enabled: true }),
    enabled: open,
    staleTime: 30000,
  })

  const devices = devicesData?.devices ?? []

  // Filter devices based on search
  const filteredDevices = search
    ? devices.filter(
        (d) =>
          d.hostname.toLowerCase().includes(search.toLowerCase()) ||
          d.mgmt_ip.toLowerCase().includes(search.toLowerCase())
      ).slice(0, 5)
    : devices.slice(0, 5)

  // Global keyboard shortcut
  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault()
        setOpen((prev) => !prev)
      }
    }
    document.addEventListener('keydown', down)
    return () => document.removeEventListener('keydown', down)
  }, [])

  const runAction = useCallback(
    (action: () => void) => {
      setOpen(false)
      setSearch('')
      action()
    },
    []
  )

  const handleDeviceSSH = (device: Device) => {
    runAction(() => {
      if (onOpenTerminal) {
        onOpenTerminal(device)
      } else {
        // Navigate to devices page with terminal query param
        navigate(`/devices?terminal=${device.id}`)
      }
    })
  }

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput
        placeholder="Type a command or search devices..."
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Quick navigation */}
        <CommandGroup heading="Navigation">
          <CommandItem onSelect={() => runAction(() => navigate('/devices'))}>
            <Server className="mr-2 h-4 w-4" />
            <span>Devices</span>
            <CommandShortcut>Go</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runAction(() => navigate('/commands'))}>
            <Play className="mr-2 h-4 w-4" />
            <span>Run Commands</span>
            <CommandShortcut>Go</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runAction(() => navigate('/jobs'))}>
            <Briefcase className="mr-2 h-4 w-4" />
            <span>Jobs</span>
            <CommandShortcut>Go</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runAction(() => navigate('/compliance'))}>
            <Shield className="mr-2 h-4 w-4" />
            <span>Compliance</span>
            <CommandShortcut>Go</CommandShortcut>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Admin pages */}
        <CommandGroup heading="Administration">
          <CommandItem onSelect={() => runAction(() => navigate('/admin?tab=users'))}>
            <Users className="mr-2 h-4 w-4" />
            <span>Users</span>
          </CommandItem>
          <CommandItem onSelect={() => runAction(() => navigate('/admin?tab=credentials'))}>
            <Key className="mr-2 h-4 w-4" />
            <span>Credentials</span>
          </CommandItem>
          <CommandItem onSelect={() => runAction(() => navigate('/admin?tab=customers'))}>
            <Building2 className="mr-2 h-4 w-4" />
            <span>Customers</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Device search results */}
        {filteredDevices.length > 0 && (
          <>
            <CommandGroup heading="Devices">
              {filteredDevices.map((device) => (
                <CommandItem
                  key={device.id}
                  value={`device-${device.id}-${device.hostname}`}
                  onSelect={() => handleDeviceSSH(device)}
                >
                  <Terminal className="mr-2 h-4 w-4" />
                  <div className="flex flex-col">
                    <span>{device.hostname}</span>
                    <span className="text-xs text-muted-foreground">{device.mgmt_ip}</span>
                  </div>
                  <CommandShortcut>SSH</CommandShortcut>
                </CommandItem>
              ))}
            </CommandGroup>
            <CommandSeparator />
          </>
        )}

        {/* Quick actions */}
        <CommandGroup heading="Quick Actions">
          <CommandItem
            onSelect={() => runAction(() => navigate('/commands'))}
          >
            <Play className="mr-2 h-4 w-4" />
            <span>Run commands on devices</span>
          </CommandItem>
          <CommandItem
            onSelect={() => runAction(() => navigate('/devices'))}
          >
            <Search className="mr-2 h-4 w-4" />
            <span>Search all devices</span>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Theme toggle */}
        <CommandGroup heading="Appearance">
          <CommandItem
            onSelect={() => runAction(() => setTheme('light'))}
          >
            <Sun className="mr-2 h-4 w-4" />
            <span>Light mode</span>
            {theme === 'light' && <CommandShortcut>Active</CommandShortcut>}
          </CommandItem>
          <CommandItem
            onSelect={() => runAction(() => setTheme('dark'))}
          >
            <Moon className="mr-2 h-4 w-4" />
            <span>Dark mode</span>
            {theme === 'dark' && <CommandShortcut>Active</CommandShortcut>}
          </CommandItem>
          <CommandItem
            onSelect={() => runAction(() => setTheme('system'))}
          >
            <Monitor className="mr-2 h-4 w-4" />
            <span>System theme</span>
            {theme === 'system' && <CommandShortcut>Active</CommandShortcut>}
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
