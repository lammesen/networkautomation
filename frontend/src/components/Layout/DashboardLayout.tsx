import { Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

export default function DashboardLayout() {
  const { user, clearAuth } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    clearAuth()
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside style={{ 
        width: '250px', 
        backgroundColor: '#2c3e50', 
        color: 'white',
        padding: '1rem'
      }}>
        <h2 style={{ marginBottom: '2rem' }}>NetAutomation</h2>
        <nav>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ marginBottom: '0.5rem' }}>
              <Link to="/devices" style={{ color: 'white', textDecoration: 'none' }}>
                📱 Devices
              </Link>
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <Link to="/commands" style={{ color: 'white', textDecoration: 'none' }}>
                ⌨️ Commands
              </Link>
            </li>
            <li style={{ marginBottom: '0.5rem' }}>
              <Link to="/jobs" style={{ color: 'white', textDecoration: 'none' }}>
                📋 Jobs
              </Link>
            </li>
          </ul>
        </nav>
      </aside>

      {/* Main content */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Top bar */}
        <header style={{ 
          backgroundColor: 'white', 
          borderBottom: '1px solid #ddd',
          padding: '1rem 2rem',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div></div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span>{user?.username} ({user?.role})</span>
            <button 
              onClick={handleLogout}
              style={{
                padding: '0.5rem 1rem',
                backgroundColor: '#dc3545',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Logout
            </button>
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, padding: '2rem', backgroundColor: '#f5f5f5' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
