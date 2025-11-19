import { ReactNode } from 'react';
import { Link } from 'react-router-dom';

interface Props {
  children: ReactNode;
  onLogout: () => void;
}

const DashboardLayout = ({ children, onLogout }: Props) => (
  <div className="app-shell" style={{ display: 'flex', minHeight: '100vh' }}>
    <aside style={{ width: 220, background: '#0f172a', color: '#fff', padding: '1rem' }}>
      <h1 style={{ fontSize: '1.4rem' }}>NetAuto</h1>
      <nav>
        <ul style={{ listStyle: 'none', padding: 0 }}>
          <li><Link to="/devices">Devices</Link></li>
          <li><Link to="/commands">Run Commands</Link></li>
          <li><Link to="/config/backup">Config Backup</Link></li>
          <li><Link to="/config/deploy">Config Deploy</Link></li>
          <li><Link to="/compliance">Compliance</Link></li>
          <li><Link to="/jobs">Jobs</Link></li>
        </ul>
      </nav>
      <button type="button" onClick={onLogout} style={{ marginTop: '2rem' }}>
        Sign out
      </button>
    </aside>
    <main style={{ flex: 1, padding: '2rem', background: '#f8fafc' }}>{children}</main>
  </div>
);

export default DashboardLayout;
