import { FormEvent, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createHttpClient } from '../../api/http';

interface Props {
  token: string;
}

const ConfigBackupPage = ({ token }: Props) => {
  const api = useMemo(() => createHttpClient(token), [token]);
  const [deviceIds, setDeviceIds] = useState('');
  const [source, setSource] = useState('manual');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    const targets = deviceIds
      ? { device_ids: deviceIds.split(',').map((id) => parseInt(id.trim(), 10)).filter((id) => !Number.isNaN(id)) }
      : { device_ids: [] };
    const response = await api.post('/automation/backup', {
      targets,
      source,
    });
    setSubmitting(false);
    navigate(`/jobs/${response.data.job_id}`);
  };

  return (
    <section>
      <h2>Configuration backups</h2>
      <p>Trigger a backup job on-demand.</p>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 600 }}>
        <label>
          Device IDs (comma separated)
          <input value={deviceIds} onChange={(e) => setDeviceIds(e.target.value)} placeholder="Leave empty for all" />
        </label>
        <label>
          Source label
          <input value={source} onChange={(e) => setSource(e.target.value)} />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Dispatching...' : 'Run backup job'}
        </button>
      </form>
    </section>
  );
};

export default ConfigBackupPage;
