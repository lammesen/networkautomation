import { Link, useLocation } from 'react-router-dom'
import {
  Briefcase,
  KeyRound,
  ListChecks,
  Server,
  ShieldCheck,
  Terminal,
  Users,
  Network,
  LogOut,
  ChevronUp,
  Sun,
  Moon,
  Monitor,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from '@/components/ui/sidebar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useAuthStore } from '@/store/authStore'
import { useUIStore } from '@/store/uiStore'
import { CustomerSelector } from './CustomerSelector'

const navSections = [
  {
    id: 'operations',
    label: 'Operations',
    items: [
      { to: '/devices', label: 'Devices', icon: Server },
      { to: '/jobs', label: 'Jobs', icon: ListChecks },
    ],
  },
  {
    id: 'automation',
    label: 'Automation',
    items: [
      { to: '/commands', label: 'Commands', icon: Terminal },
      { to: '/compliance', label: 'Compliance', icon: ShieldCheck },
    ],
  },
  {
    id: 'admin',
    label: 'Administration',
    adminOnly: true,
    items: [
      { to: '/admin', label: 'Admin', icon: Users },
    ],
  },
]

function getUserInitials(username: string): string {
  return username
    .split(/[._-]/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || '')
    .join('')
}

interface AppSidebarProps {
  onLogout: () => void
}

export function AppSidebar({ onLogout }: AppSidebarProps) {
  const location = useLocation()
  const user = useAuthStore((s) => s.user)
  const theme = useUIStore((s) => s.theme)
  const setTheme = useUIStore((s) => s.setTheme)

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(`${path}/`)

  const visibleSections = navSections.filter(
    (section) => !section.adminOnly || user?.role === 'admin'
  )

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <Link to="/devices">
                <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Network className="size-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">NetAutomation</span>
                  <span className="text-xs text-muted-foreground">v1.0</span>
                </div>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <CustomerSelector />
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {visibleSections.map((section) => (
          <SidebarGroup key={section.id}>
            <SidebarGroupLabel>{section.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items.map((item) => (
                  <SidebarMenuItem key={item.to}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive(item.to)}
                      tooltip={item.label}
                    >
                      <Link to={item.to}>
                        <item.icon className="size-4" />
                        <span>{item.label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton
                  size="lg"
                  className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
                >
                  <Avatar className="h-8 w-8 rounded-lg">
                    <AvatarFallback className="rounded-lg bg-primary text-primary-foreground text-xs">
                      {user?.username ? getUserInitials(user.username) : 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">{user?.username}</span>
                    <span className="truncate text-xs text-muted-foreground capitalize">
                      {user?.role}
                    </span>
                  </div>
                  <ChevronUp className="ml-auto size-4" />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent
                className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
                side="top"
                align="end"
                sideOffset={4}
              >
                <div className="flex items-center gap-2 px-2 py-1.5 text-left text-sm">
                  <Avatar className="h-8 w-8 rounded-lg">
                    <AvatarFallback className="rounded-lg bg-primary text-primary-foreground text-xs">
                      {user?.username ? getUserInitials(user.username) : 'U'}
                    </AvatarFallback>
                  </Avatar>
                  <div className="grid flex-1 text-left text-sm leading-tight">
                    <span className="truncate font-semibold">{user?.username}</span>
                    <span className="truncate text-xs text-muted-foreground capitalize">
                      {user?.role}
                    </span>
                  </div>
                </div>
                <DropdownMenuSeparator />
                {user?.role === 'admin' && (
                  <>
                    <DropdownMenuItem asChild>
                      <Link to="/admin" className="flex items-center gap-2">
                        <Users className="size-4" />
                        User Management
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/admin?tab=credentials" className="flex items-center gap-2">
                        <KeyRound className="size-4" />
                        Credentials
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link to="/admin?tab=customers" className="flex items-center gap-2">
                        <Briefcase className="size-4" />
                        Customers
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                  </>
                )}
                <DropdownMenuSub>
                  <DropdownMenuSubTrigger>
                    {theme === 'dark' ? (
                      <Moon className="size-4 mr-2" />
                    ) : theme === 'light' ? (
                      <Sun className="size-4 mr-2" />
                    ) : (
                      <Monitor className="size-4 mr-2" />
                    )}
                    Theme
                  </DropdownMenuSubTrigger>
                  <DropdownMenuSubContent>
                    <DropdownMenuRadioGroup value={theme} onValueChange={(v) => setTheme(v as 'light' | 'dark' | 'system')}>
                      <DropdownMenuRadioItem value="light">
                        <Sun className="size-4 mr-2" />
                        Light
                      </DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="dark">
                        <Moon className="size-4 mr-2" />
                        Dark
                      </DropdownMenuRadioItem>
                      <DropdownMenuRadioItem value="system">
                        <Monitor className="size-4 mr-2" />
                        System
                      </DropdownMenuRadioItem>
                    </DropdownMenuRadioGroup>
                  </DropdownMenuSubContent>
                </DropdownMenuSub>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={onLogout} className="text-destructive">
                  <LogOut className="size-4 mr-2" />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
