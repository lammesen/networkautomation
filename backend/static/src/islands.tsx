import React from "react";
import { createRoot, Root } from "react-dom/client";

// Import all UI components for use in islands
import { Button } from "./components/ui/button";
import { Badge } from "./components/ui/badge";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "./components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "./components/ui/table";
import { Input } from "./components/ui/input";
import { Label } from "./components/ui/label";
import { Checkbox } from "./components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./components/ui/select";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "./components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "./components/ui/dropdown-menu";
import { Alert, AlertDescription, AlertTitle } from "./components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "./components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./components/ui/tooltip";
import { Avatar, AvatarFallback, AvatarImage } from "./components/ui/avatar";
import { Separator } from "./components/ui/separator";
import { Progress } from "./components/ui/progress";
import { Skeleton } from "./components/ui/skeleton";
import { Switch } from "./components/ui/switch";
import { Textarea } from "./components/ui/textarea";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from "./components/ui/sheet";
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator } from "./components/ui/breadcrumb";
import { ScrollArea } from "./components/ui/scroll-area";
import { Popover, PopoverContent, PopoverTrigger } from "./components/ui/popover";
import { Spinner } from "./components/ui/spinner";
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
  SidebarTrigger,
  SidebarInset
} from "./components/ui/sidebar";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./components/ui/collapsible";
import DataTable from "./components/islands/DataTable";
import JobsTable from "./components/islands/JobsTable";
import SnapshotsTable from "./components/islands/SnapshotsTable";
import CompliancePoliciesTable from "./components/islands/CompliancePoliciesTable";
import ComplianceResultsTable from "./components/islands/ComplianceResultsTable";
import TopologyTable from "./components/islands/TopologyTable";
import TopologyMap from "./components/islands/TopologyMap";
import GeoNetworkMap from "./components/islands/GeoNetworkMap";
import JobLogs from "./components/islands/JobLogs";
import FormSelect from "./components/islands/FormSelect";
import { AppSidebar } from "./components/islands/AppSidebar";
import { AppHeader } from "./components/islands/AppHeader";
import { CommandPalette, CommandPaletteButton } from "./components/islands/CommandPalette";
import { Toaster } from "./components/ui/sonner";
import { BaseDataTable } from "./components/islands/BaseDataTable";
import { FilterBar } from "./components/islands/FilterBar";
import { BulkActionBar } from "./components/islands/BulkActionBar";
import { ConfirmDialog } from "./components/islands/ConfirmDialog";
import SSHTerminal from "./components/islands/SSHTerminal";

// Import xterm.js CSS
import "@xterm/xterm/css/xterm.css";

// Island component registry - maps data-island names to React components
const islandComponents: Record<string, React.ComponentType<any>> = {
  DataTable,
  JobsTable,
  SnapshotsTable,
  CompliancePoliciesTable,
  ComplianceResultsTable,
  TopologyTable,
  TopologyMap,
  GeoNetworkMap,
  JobLogs,
  FormSelect,
  AppSidebar,
  AppHeader,
  CommandPalette,
  CommandPaletteButton,
  Toaster,
  BaseDataTable,
  FilterBar,
  BulkActionBar,
  ConfirmDialog,
  SSHTerminal,
};

// Store roots to prevent memory leaks on re-hydration
const roots = new WeakMap<Element, Root>();

/**
 * Hydrate all islands in a given container
 * Scans for elements with data-island attribute and mounts corresponding React components
 */
function hydrateIslands(container: Element | Document = document): void {
  const islands = container.querySelectorAll("[data-island]");
  console.log(`[Islands] Found ${islands.length} islands to hydrate`);
  
  islands.forEach((island) => {
    const componentName = island.getAttribute("data-island");
    if (!componentName) return;

    console.log(`[Islands] Hydrating: ${componentName}`);
    
    const Component = islandComponents[componentName];
    if (!Component) {
      console.warn(`Island component "${componentName}" not found in registry`);
      return;
    }

    // Parse props from data-props attribute
    let props = {};
    const propsAttr = island.getAttribute("data-props");
    if (propsAttr) {
      try {
        props = JSON.parse(propsAttr);
        console.log(`[Islands] ${componentName} props parsed:`, Object.keys(props));
      } catch (e) {
        console.error(`Failed to parse props for island "${componentName}":`, e);
      }
    }

    // Get or create root
    let root = roots.get(island);
    if (!root) {
      console.log(`[Islands] Creating new root for ${componentName}`);
      root = createRoot(island);
      roots.set(island, root);
    } else {
      console.log(`[Islands] Reusing existing root for ${componentName}`);
    }

    // Render the component
    console.log(`[Islands] Rendering ${componentName}...`);
    try {
      root.render(
        <React.StrictMode>
          <TooltipProvider>
            <Component {...props} />
          </TooltipProvider>
        </React.StrictMode>
      );
      console.log(`[Islands] ${componentName} render called successfully`);
    } catch (e) {
      console.error(`[Islands] Error rendering ${componentName}:`, e);
    }
  });
}

// Initial hydration on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => hydrateIslands());
} else {
  hydrateIslands();
}

// Re-hydrate after HTMX content swaps
document.body.addEventListener("htmx:afterSwap", (event: Event) => {
  const target = (event as CustomEvent).detail?.target;
  if (target instanceof Element) {
    hydrateIslands(target);
  }
});

// Re-hydrate after HTMX settles (for delayed content)
document.body.addEventListener("htmx:afterSettle", (event: Event) => {
  const target = (event as CustomEvent).detail?.target;
  if (target instanceof Element) {
    hydrateIslands(target);
  }
});

// Export for potential external use
declare global {
  interface Window {
    hydrateIslands: typeof hydrateIslands;
  }
}
window.hydrateIslands = hydrateIslands;

// Export components for use in custom islands
export {
  // Core
  Button,
  Badge,
  Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter,
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
  Input,
  Label,
  Checkbox,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
  Alert, AlertDescription, AlertTitle,
  Tabs, TabsContent, TabsList, TabsTrigger,
  Tooltip, TooltipContent, TooltipProvider, TooltipTrigger,
  Avatar, AvatarFallback, AvatarImage,
  Separator,
  Progress,
  Skeleton,
  Switch,
  Textarea,
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger,
  Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbPage, BreadcrumbSeparator,
  ScrollArea,
  Popover, PopoverContent, PopoverTrigger,
  Spinner,
  Sidebar, SidebarContent, SidebarFooter, SidebarGroup, SidebarGroupContent, SidebarGroupLabel, 
  SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, SidebarProvider, SidebarTrigger, SidebarInset,
  Collapsible, CollapsibleContent, CollapsibleTrigger,
};
