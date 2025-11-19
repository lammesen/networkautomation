import { Navigate, Route, Routes } from 'react-router-dom';
import { useEffect, useState } from 'react';
import DashboardLayout from '../components/DashboardLayout';
import DevicesPage from '../features/devices/DevicesPage';
import JobsPage from '../features/jobs/JobsPage';
import JobDetailPage from '../features/jobs/JobDetailPage';
import LoginPage from '../features/auth/LoginPage';
import RunCommandsPage from '../features/commands/RunCommandsPage';
import ConfigBackupPage from '../features/config/ConfigBackupPage';
import ConfigDeployPage from '../features/config/ConfigDeployPage';
import CompliancePage from '../features/compliance/CompliancePage';

const App = () => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));

  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
    } else {
      localStorage.removeItem('token');
    }
  }, [token]);

  if (!token) {
    return <LoginPage onAuthenticated={setToken} />;
  }

  return (
    <DashboardLayout onLogout={() => setToken(null)}>
      <Routes>
        <Route path="/" element={<Navigate to="/devices" />} />
        <Route path="/devices" element={<DevicesPage token={token} />} />
        <Route path="/jobs" element={<JobsPage token={token} />} />
        <Route path="/jobs/:jobId" element={<JobDetailPage token={token} />} />
        <Route path="/commands" element={<RunCommandsPage token={token} />} />
        <Route path="/config/backup" element={<ConfigBackupPage token={token} />} />
        <Route path="/config/deploy" element={<ConfigDeployPage token={token} />} />
        <Route path="/compliance" element={<CompliancePage token={token} />} />
      </Routes>
    </DashboardLayout>
  );
};

export default App;
