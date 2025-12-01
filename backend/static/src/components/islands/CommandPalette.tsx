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
  Users,
  Search,
} from "lucide-react";

import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

type CommandItem = {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  keywords?: string[];
};

type CommandGroup = {
  heading: string;
  items: CommandItem[];
};

const commandGroups: CommandGroup[] = [
  {
    heading: "Navigation",
    items: [
      { title: "Dashboard", icon: Home, href: "/", keywords: ["home", "overview"] },
      { title: "Devices", icon: Server, href: "/devices/", keywords: ["inventory", "hosts", "network"] },
      { title: "Topology", icon: Network, href: "/topology/", keywords: ["map", "connections", "links"] },
      { title: "Jobs", icon: RefreshCw, href: "/jobs/", keywords: ["tasks", "automation", "running"] },
    ],
  },
  {
    heading: "Configurations",
    items: [
      { title: "Config Backups", icon: FileText, href: "/config/", keywords: ["backup", "save", "restore"] },
      { title: "Config Diff", icon: GitCompare, href: "/config/diff", keywords: ["compare", "changes", "difference"] },
    ],
  },
  {
    heading: "Compliance",
    items: [
      { title: "Compliance Overview", icon: BarChart3, href: "/compliance/overview", keywords: ["status", "score"] },
      { title: "Compliance Policies", icon: ClipboardCheck, href: "/compliance/policies", keywords: ["rules", "standards"] },
      { title: "Compliance Results", icon: FileCheck, href: "/compliance/results", keywords: ["audit", "report"] },
      { title: "Run Compliance Check", icon: PlayCircle, href: "/compliance/run", keywords: ["execute", "scan"] },
    ],
  },
  {
    heading: "Tools",
    items: [
      { title: "Run Commands", icon: Terminal, href: "/commands/", keywords: ["cli", "execute", "ssh", "script"] },
      { title: "Reachability Test", icon: Wifi, href: "/reachability/", keywords: ["ping", "connectivity", "test"] },
    ],
  },
  {
    heading: "Administration",
    items: [
      { title: "Users & Roles", icon: Users, href: "/admin/", keywords: ["permissions", "accounts", "settings"] },
    ],
  },
];

type CommandPaletteProps = {
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
};

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const [isOpen, setIsOpen] = React.useState(open ?? false);

  const handleOpenChange = (newOpen: boolean) => {
    setIsOpen(newOpen);
    onOpenChange?.(newOpen);
  };

  // Keyboard shortcut to open
  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        handleOpenChange(!isOpen);
      }
    };

    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, [isOpen]);

  // Sync with external open prop
  React.useEffect(() => {
    if (open !== undefined) {
      setIsOpen(open);
    }
  }, [open]);

  const handleSelect = (href: string) => {
    handleOpenChange(false);
    window.location.href = href;
  };

  return (
    <CommandDialog open={isOpen} onOpenChange={handleOpenChange}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {commandGroups.map((group, groupIndex) => (
          <React.Fragment key={group.heading}>
            {groupIndex > 0 && <CommandSeparator />}
            <CommandGroup heading={group.heading}>
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <CommandItem
                    key={item.href}
                    onSelect={() => handleSelect(item.href)}
                    keywords={item.keywords}
                  >
                    <Icon className="mr-2 h-4 w-4" />
                    <span>{item.title}</span>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </React.Fragment>
        ))}
      </CommandList>
    </CommandDialog>
  );
}

// Standalone search button that opens the command palette
export function CommandPaletteButton() {
  const [open, setOpen] = React.useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Search className="h-4 w-4" />
        <span className="hidden sm:inline">Search...</span>
        <kbd className="pointer-events-none hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium sm:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </button>
      <CommandPalette open={open} onOpenChange={setOpen} />
    </>
  );
}

export default CommandPalette;
