import { useMemo, useState } from 'react'
import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  Briefcase,
  KeyRound,
  ListChecks,
  Server,
  ShieldCheck,
  Terminal,
  Users,
  ChevronDown,
} from 'lucide-react'

export default function DashboardLayout() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  const navSections = useMemo(
    () => [
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
        label: 'Admin',
        adminOnly: true,
        items: [
          { to: '/credentials', label: 'Credentials', icon: KeyRound },
          { to: '/users', label: 'Users', icon: Users },
          { to: '/customers', label: 'Customers', icon: Briefcase },
        ],
      },
    ],
    []
  )

  const [openSections, setOpenSections] = useState<Set<string>>(new Set(['operations', 'automation']))

  const toggleSection = (id: string) => {
    setOpenSections((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const isActive = (path: string) =>
    location.pathname === path || location.pathname.startsWith(`${path}/`)

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Sidebar */}
      <aside className="w-60 bg-slate-900 text-white p-4 flex-shrink-0 border-r border-slate-800">
        <div className="flex items-center justify-between mb-6 px-2">
          <h2 className="text-lg font-semibold tracking-tight">NetAutomation</h2>
        </div>
        <nav className="space-y-4 text-sm">
          {navSections
            .filter((section) => !section.adminOnly || user?.role === 'admin')
            .map((section) => (
              <div key={section.id}>
                <button
                  className="flex w-full items-center justify-between px-2 py-2 text-left text-slate-200 hover:text-white hover:bg-slate-800 rounded-md transition"
                  onClick={() => toggleSection(section.id)}
                >
                  <span className="font-medium">{section.label}</span>
                  <ChevronDown
                    className={cn(
                      'h-4 w-4 transition-transform',
                      openSections.has(section.id) ? 'rotate-180' : 'rotate-0'
                    )}
                  />
                </button>
                {openSections.has(section.id) && (
                  <ul className="mt-1 space-y-1">
                    {section.items.map((item) => (
                      <li key={item.to}>
                        <Link to={item.to} className="block">
                          <Button
                            variant="ghost"
                            size="sm"
                            className={cn(
                              'w-full justify-start gap-2 rounded-md px-2',
                              isActive(item.to)
                                ? 'bg-slate-800 text-white hover:bg-slate-700'
                                : 'text-slate-300 hover:text-white hover:bg-slate-800'
                            )}
                          >
                            <item.icon className="h-4 w-4" />
                            {item.label}
                          </Button>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="bg-white dark:bg-slate-800 border-b p-4 flex justify-between items-center">
          <div></div>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600 dark:text-slate-300">
              {user?.username} ({user?.role})
            </span>
            <Button variant="destructive" size="sm" onClick={handleLogout}>
              Logout
            </Button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 p-8 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
