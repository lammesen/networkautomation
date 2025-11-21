import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import DashboardLayout from './components/Layout/DashboardLayout'
import DevicesPage from './pages/DevicesPage'
import JobsPage from './pages/JobsPage'
import CommandsPage from './pages/CommandsPage'
import UsersPage from './pages/UsersPage'
import CustomersPage from './pages/CustomersPage'
import CompliancePage from './pages/CompliancePage'
import CredentialsPage from './pages/CredentialsPage'
import { useAuthStore } from './store/authStore'
import { AppProviders } from '@/providers/AppProviders'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function App() {
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
            <Route path="devices" element={<DevicesPage />} />
            <Route path="jobs" element={<JobsPage />} />
            <Route path="commands" element={<CommandsPage />} />
            <Route path="compliance" element={<CompliancePage />} />
            <Route path="credentials" element={<CredentialsPage />} />
            <Route path="users" element={<UsersPage />} />
            <Route path="customers" element={<CustomersPage />} />
          </Route>
        </Routes>
      </Router>
    </AppProviders>
  )
}

export default App
