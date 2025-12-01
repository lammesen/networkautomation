import * as React from "react";
import { Bell, Search, LogOut, Settings, User } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { SidebarTrigger } from "@/components/ui/sidebar";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";

type BreadcrumbItem = {
  label: string;
  href?: string;
};

type AppHeaderProps = {
  user?: {
    username: string;
    fullName?: string;
    initials?: string;
  };
  environmentName?: string;
  breadcrumbs?: BreadcrumbItem[];
  showSearch?: boolean;
  onSearchClick?: () => void;
};

export function AppHeader({
  user,
  environmentName = "LAB",
  breadcrumbs = [],
  showSearch = true,
  onSearchClick,
}: AppHeaderProps) {
  const initials = user?.initials || user?.username?.slice(0, 2).toUpperCase() || "??";

  const handleSearchClick = () => {
    if (onSearchClick) {
      onSearchClick();
    } else {
      // Dispatch event for command palette
      document.dispatchEvent(
        new KeyboardEvent("keydown", { key: "k", metaKey: true })
      );
    }
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4">
      {/* Sidebar trigger for mobile */}
      <SidebarTrigger className="-ml-1" />
      
      <Separator orientation="vertical" className="mr-2 h-4" />

      {/* Environment badge */}
      <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
        {environmentName.toUpperCase()}
      </Badge>

      {/* Breadcrumbs */}
      {breadcrumbs.length > 0 && (
        <>
          <Separator orientation="vertical" className="mx-2 h-4" />
          <Breadcrumb>
            <BreadcrumbList>
              {breadcrumbs.map((item, index) => (
                <React.Fragment key={index}>
                  {index > 0 && <BreadcrumbSeparator />}
                  <BreadcrumbItem>
                    {item.href ? (
                      <BreadcrumbLink href={item.href}>{item.label}</BreadcrumbLink>
                    ) : (
                      <BreadcrumbPage>{item.label}</BreadcrumbPage>
                    )}
                  </BreadcrumbItem>
                </React.Fragment>
              ))}
            </BreadcrumbList>
          </Breadcrumb>
        </>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search button */}
      {showSearch && (
        <Button
          variant="outline"
          className="relative h-9 w-9 p-0 xl:h-9 xl:w-60 xl:justify-start xl:px-3 xl:py-2"
          onClick={handleSearchClick}
        >
          <Search className="h-4 w-4 xl:mr-2" />
          <span className="hidden xl:inline-flex">Search...</span>
          <kbd className="pointer-events-none absolute right-1.5 top-1.5 hidden h-6 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 xl:flex">
            <span className="text-xs">⌘</span>K
          </kbd>
        </Button>
      )}

      {/* Notifications */}
      <Button variant="ghost" size="icon" className="h-9 w-9">
        <Bell className="h-4 w-4" />
        <span className="sr-only">Notifications</span>
      </Button>

      {/* User menu */}
      {user && (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarFallback className="bg-primary text-primary-foreground text-xs font-medium">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">{user.username}</p>
                <p className="text-xs leading-none text-muted-foreground">
                  {user.fullName || "Administrator"}
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <a href="/admin/">
                <User className="mr-2 h-4 w-4" />
                Profile
              </a>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <a href="/admin/">
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </a>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild className="text-destructive focus:text-destructive">
              <a href="/logout/">
                <LogOut className="mr-2 h-4 w-4" />
                Sign out
              </a>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </header>
  );
}

export default AppHeader;
