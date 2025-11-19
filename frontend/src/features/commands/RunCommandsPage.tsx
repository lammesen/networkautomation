import { FormEvent, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createHttpClient } from '../../api/http';

interface Props {
  token: string;
}

const RunCommandsPage = ({ token }: Props) => {
  const api = useMemo(() => createHttpClient(token), [token]);
  const [deviceIds, setDeviceIds] = useState('');
  const [commands, setCommands] = useState('show version');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    const targets = deviceIds
      ? { device_ids: deviceIds.split(',').map((id) => parseInt(id.trim(), 10)).filter((id) => !Number.isNaN(id)) }
      : { device_ids: [] };
    const response = await api.post('/automation/commands', {
      targets,
      commands: commands.split('\n').filter(Boolean),
    });
    setSubmitting(false);
    navigate(`/jobs/${response.data.job_id}`);
  };

  return (
    <section>
      <h2>Run ad-hoc commands</h2>
      <p>Select devices and issue multi-line command sets.</p>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 600 }}>
        <label>
          Device IDs (comma separated)
          <input value={deviceIds} onChange={(e) => setDeviceIds(e.target.value)} placeholder="Leave empty for all" />
        </label>
        <label>
          Commands
          <textarea rows={6} value={commands} onChange={(e) => setCommands(e.target.value)} />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? 'Dispatching job...' : 'Run commands'}
        </button>
      </form>
    </section>
  );
};

export default RunCommandsPage;
