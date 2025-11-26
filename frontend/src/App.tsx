import { lazy, Suspense, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import { useUIStore } from './store/uiStore'
import { AppProviders } from '@/providers/AppProviders'
import { ErrorBoundary } from '@/components/layout/ErrorBoundary'
import { LoadingSpinner } from '@/components/ui/query-state'

// Eager load - needed immediately
import LoginPage from './pages/LoginPage'
import DashboardLayout from '@/components/layout/DashboardLayout'

// Lazy load feature pages for code splitting
const DevicesPage = lazy(() => import('./pages/DevicesPage'))
const DeviceDetailPage = lazy(() => import('./pages/DeviceDetailPage'))
const JobsPage = lazy(() => import('./pages/JobsPage'))
const CommandsPage = lazy(() => import('./pages/CommandsPage'))
const CompliancePage = lazy(() => import('./pages/CompliancePage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((state) => state.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

/**
 * Wraps a lazy-loaded component with Suspense and ErrorBoundary
 */
function LazyRoute({ children }: { children: React.ReactNode }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner message="Loading..." />}>
        {children}
      </Suspense>
    </ErrorBoundary>
  )
}

function App() {
  const theme = useUIStore((s) => s.theme)

  // Listen for system theme changes when theme is set to 'system'
  useEffect(() => {
    if (theme !== 'system') return

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    const handleChange = () => {
      const root = window.document.documentElement
      root.classList.remove('light', 'dark')
      root.classList.add(mediaQuery.matches ? 'dark' : 'light')
    }

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [theme])

  return (
    <AppProviders>
      <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <DashboardLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/devices" replace />} />
            <Route
              path="devices"
              element={
                <LazyRoute>
                  <DevicesPage />
                </LazyRoute>
              }
            />
            <Route
              path="devices/:id"
              element={
                <LazyRoute>
                  <DeviceDetailPage />
                </LazyRoute>
              }
            />
            <Route
              path="jobs"
              element={
                <LazyRoute>
                  <JobsPage />
                </LazyRoute>
              }
            />
            <Route path="admin/jobs" element={<Navigate to="/jobs" replace />} />
            <Route
              path="commands"
              element={
                <LazyRoute>
                  <CommandsPage />
                </LazyRoute>
              }
            />
            <Route
              path="compliance"
              element={
                <LazyRoute>
                  <CompliancePage />
                </LazyRoute>
              }
            />
            <Route
              path="admin"
              element={
                <LazyRoute>
                  <AdminPage />
                </LazyRoute>
              }
            />
            {/* Redirects for old routes */}
            <Route path="credentials" element={<Navigate to="/admin?tab=credentials" replace />} />
            <Route path="users" element={<Navigate to="/admin?tab=users" replace />} />
            <Route path="customers" element={<Navigate to="/admin?tab=customers" replace />} />
            <Route
              path="*"
              element={
                <LazyRoute>
                  <NotFoundPage />
                </LazyRoute>
              }
            />
          </Route>
          {/* Catch-all 404 for routes outside dashboard */}
          <Route
            path="*"
            element={
              <LazyRoute>
                <NotFoundPage />
              </LazyRoute>
            }
          />
        </Routes>
      </Router>
    </AppProviders>
  )
}

export default App
