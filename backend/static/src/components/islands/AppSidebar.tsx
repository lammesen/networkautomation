import * as React from "react";
import {
  Home,
  Server,
  Network,
  RefreshCw,
  FileText,
  GitCompare,
  BarChart3,
  ClipboardCheck,
  FileCheck,
  PlayCircle,
  Terminal,
  Wifi,
  Calendar,
  FileBarChart,
  Users,
  Clock,
  LogOut,
  ChevronRight,
  PanelLeftClose,
  PanelLeft,
  Globe2,
} from "lucide-react";

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
  SidebarProvider,
  SidebarRail,
  SidebarInset,
  useSidebar,
} from "@/components/ui/sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

// Navigation structure for network automation app
const navigation = {
  home: [
    { title: "Dashboard", icon: Home, href: "/", isActive: (path: string) => path === "/" },
  ],
  inventory: [
    { title: "Devices", icon: Server, href: "/devices/", isActive: (path: string) => path.startsWith("/devices") },
    { title: "Topology", icon: Network, href: "/topology/", isActive: (path: string) => path.startsWith("/topology") },
    { title: "Geo Map", icon: Globe2, href: "/maps/geo/", isActive: (path: string) => path.startsWith("/maps/geo") },
  ],
  jobs: [
    { title: "Jobs", icon: RefreshCw, href: "/jobs/", isActive: (path: string) => path.startsWith("/jobs") },
  ],
  configurations: [
    { title: "Backups", icon: FileText, href: "/config/", isActive: (path: string) => path === "/config/" },
    { title: "Config Diff", icon: GitCompare, href: "/config/diff", isActive: (path: string) => path.startsWith("/config/diff") },
  ],
  compliance: [
    { title: "Overview", icon: BarChart3, href: "/compliance/overview", isActive: (path: string) => path.includes("/compliance/overview") },
    { title: "Policies", icon: ClipboardCheck, href: "/compliance/policies", isActive: (path: string) => path.includes("/compliance/policies") },
    { title: "Results", icon: FileCheck, href: "/compliance/results", isActive: (path: string) => path.includes("/compliance/results") },
    { title: "Run Check", icon: PlayCircle, href: "/compliance/run", isActive: (path: string) => path === "/compliance/run" },
  ],
  tools: [
    { title: "Run Commands", icon: Terminal, href: "/commands/", isActive: (path: string) => path.startsWith("/commands") },
    { title: "Reachability", icon: Wifi, href: "/reachability/", isActive: (path: string) => path.startsWith("/reachability") },
  ],
  scheduling: [
    { title: "Schedules", icon: Calendar, href: "#", disabled: true, comingSoon: true },
  ],
  reports: [
    { title: "Reports", icon: FileBarChart, href: "#", disabled: true, comingSoon: true },
  ],
  admin: [
    { title: "Users & Roles", icon: Users, href: "/admin/", isActive: () => false },
    { title: "Audit Log", icon: Clock, href: "#", disabled: true, comingSoon: true },
  ],
};

type NavItem = {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  isActive?: (path: string) => boolean;
  disabled?: boolean;
  comingSoon?: boolean;
};

type NavGroup = {
  label: string;
  items: NavItem[];
  collapsible?: boolean;
  defaultOpen?: boolean;
};

const navGroups: NavGroup[] = [
  { label: "Home", items: navigation.home },
  { label: "Inventory", items: navigation.inventory },
  { label: "Jobs", items: navigation.jobs },
  { label: "Configurations", items: navigation.configurations },
  { label: "Compliance", items: navigation.compliance, collapsible: true, defaultOpen: true },
  { label: "Tools", items: navigation.tools },
  { label: "Scheduling", items: navigation.scheduling },
  { label: "Reports", items: navigation.reports },
  { label: "Admin", items: navigation.admin },
];

type AppSidebarProps = {
  user?: {
    username: string;
    fullName?: string;
    initials?: string;
  };
  currentPath?: string;
};

function NavGroup({ group, currentPath }: { group: NavGroup; currentPath: string }) {
  const [isOpen, setIsOpen] = React.useState(group.defaultOpen ?? true);

  if (group.collapsible) {
    return (
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <SidebarGroup>
          <CollapsibleTrigger asChild>
            <SidebarGroupLabel className="cursor-pointer hover:bg-sidebar-accent/50 rounded-md">
              <span className="flex-1">{group.label}</span>
              <ChevronRight
                className={cn(
                  "h-4 w-4 transition-transform duration-200",
                  isOpen && "rotate-90"
                )}
              />
            </SidebarGroupLabel>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => (
                  <NavItem key={item.href} item={item} currentPath={currentPath} />
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </CollapsibleContent>
        </SidebarGroup>
      </Collapsible>
    );
  }

  return (
    <SidebarGroup>
      <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {group.items.map((item) => (
            <NavItem key={item.href} item={item} currentPath={currentPath} />
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

function NavItem({ item, currentPath }: { item: NavItem; currentPath: string }) {
  const isActive = item.isActive?.(currentPath) ?? false;
  const Icon = item.icon;

  if (item.disabled) {
    return (
      <SidebarMenuItem>
        <SidebarMenuButton
          disabled
          tooltip={item.comingSoon ? "Coming soon" : undefined}
          className="text-muted-foreground cursor-not-allowed"
        >
          <Icon className="h-4 w-4" />
          <span>{item.title}</span>
          {item.comingSoon && (
            <span className="ml-auto text-[10px] text-muted-foreground">Soon</span>
          )}
        </SidebarMenuButton>
      </SidebarMenuItem>
    );
  }

  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={isActive} tooltip={item.title}>
        <a href={item.href}>
          <Icon className="h-4 w-4" />
          <span>{item.title}</span>
        </a>
      </SidebarMenuButton>
    </SidebarMenuItem>
  );
}

function SidebarToggle() {
  const { state, toggleSidebar } = useSidebar();
  const isCollapsed = state === "collapsed";

  return (
    <Button
      variant="ghost"
      size="icon"
      className="h-7 w-7"
      onClick={toggleSidebar}
      title={isCollapsed ? "Expand sidebar (Ctrl+B)" : "Collapse sidebar (Ctrl+B)"}
    >
      {isCollapsed ? (
        <PanelLeft className="h-4 w-4" />
      ) : (
        <PanelLeftClose className="h-4 w-4" />
      )}
    </Button>
  );
}

function UserFooter({ user }: { user: AppSidebarProps["user"] }) {
  if (!user) return null;

  const initials = user.initials || user.username.slice(0, 2).toUpperCase();

  return (
    <SidebarFooter>
      <SidebarMenu>
        <SidebarMenuItem>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <SidebarMenuButton
                size="lg"
                className="data-[state=open]:bg-sidebar-accent"
              >
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary text-primary-foreground text-xs">
                    {initials}
                  </AvatarFallback>
                </Avatar>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-medium">{user.username}</span>
                  <span className="text-xs text-muted-foreground">
                    {user.fullName || "Administrator"}
                  </span>
                </div>
              </SidebarMenuButton>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              className="w-[--radix-dropdown-menu-trigger-width]"
              align="start"
              side="top"
            >
              <DropdownMenuItem asChild>
                <a href="/admin/">
                  <Users className="mr-2 h-4 w-4" />
                  Account Settings
                </a>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild className="text-destructive">
                <a href="/logout/">
                  <LogOut className="mr-2 h-4 w-4" />
                  Sign out
                </a>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </SidebarMenuItem>
      </SidebarMenu>
    </SidebarFooter>
  );
}

function AppSidebarInner({ user, currentPath = "/" }: AppSidebarProps) {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="border-b">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild>
              <a href="/" className="flex items-center gap-2">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Server className="h-4 w-4" />
                </div>
                <div className="flex flex-col gap-0.5 leading-none">
                  <span className="font-semibold">webnet</span>
                  <span className="text-xs text-muted-foreground">NetOps Console</span>
                </div>
              </a>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      
      <SidebarContent>
        {navGroups.map((group) => (
          <NavGroup key={group.label} group={group} currentPath={currentPath} />
        ))}
      </SidebarContent>
      
      <UserFooter user={user} />
      <SidebarRail />
    </Sidebar>
  );
}

export function AppSidebar(props: AppSidebarProps) {
  return (
    <SidebarProvider defaultOpen>
      <AppSidebarInner {...props} />
    </SidebarProvider>
  );
}

// Wrapper component that includes SidebarInset for main content
export function AppLayout({
  user,
  currentPath,
  children,
}: AppSidebarProps & { children?: React.ReactNode }) {
  return (
    <SidebarProvider defaultOpen>
      <AppSidebarInner user={user} currentPath={currentPath} />
      <SidebarInset>
        <div className="flex flex-1 flex-col">
          {children}
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

// Export the toggle for use in header
export { SidebarToggle };

export default AppSidebar;
