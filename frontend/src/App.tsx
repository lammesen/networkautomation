import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LoginPage from './pages/LoginPage'
import DashboardLayout from './components/Layout/DashboardLayout'
import DevicesPage from './pages/DevicesPage'
import JobsPage from './pages/JobsPage'
import CommandsPage from './pages/CommandsPage'
import { useAuthStore } from './store/authStore'

const queryClient = new QueryClient()

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <Router>
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
            <Route path="devices" element={<DevicesPage />} />
            <Route path="jobs" element={<JobsPage />} />
            <Route path="commands" element={<CommandsPage />} />
          </Route>
        </Routes>
      </Router>
    </QueryClientProvider>
  )
}

export default App
