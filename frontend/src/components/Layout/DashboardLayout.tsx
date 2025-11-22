import { Outlet, Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export default function DashboardLayout() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  const navItems = [
    { to: '/devices', label: 'Devices' },
    { to: '/commands', label: 'Commands' },
    { to: '/jobs', label: 'Jobs' },
    { to: '/compliance', label: 'Compliance' },
    { to: '/credentials', label: 'Credentials' },
  ]

  if (user?.role === 'admin') {
    navItems.push({ to: '/users', label: 'Users' })
    navItems.push({ to: '/customers', label: 'Customers' })
  }

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-slate-900">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 text-white p-4 flex-shrink-0">
        <h2 className="text-xl font-bold mb-8 px-4">NetAutomation</h2>
        <nav>
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.to}>
                <Link to={item.to} className="block">
                  <Button
                    variant="ghost"
                    className={cn(
                      "w-full justify-start",
                      location.pathname.startsWith(item.to) 
                        ? "bg-slate-800 text-white hover:bg-slate-700" 
                        : "text-slate-300 hover:text-white hover:bg-slate-800"
                    )}
                  >
                    {item.label}
                  </Button>
                </Link>
              </li>
            ))}
          </ul>
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