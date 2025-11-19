import { FormEvent, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createHttpClient } from '../../api/http';

interface Props {
  token: string;
}

const ConfigDeployPage = ({ token }: Props) => {
  const api = useMemo(() => createHttpClient(token), [token]);
  const [deviceIds, setDeviceIds] = useState('');
  const [snippet, setSnippet] = useState('interface Loopback10\n description provisioned by NetAuto');
  const [previewJobId, setPreviewJobId] = useState<number | null>(null);
  const [diffs, setDiffs] = useState<Record<string, { diff: string }>>({});
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const buildTargets = () =>
    deviceIds
      ? { device_ids: deviceIds.split(',').map((id) => parseInt(id.trim(), 10)).filter((id) => !Number.isNaN(id)) }
      : { device_ids: [] };

  const handlePreview = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    const response = await api.post('/automation/deploy/preview', {
      targets: buildTargets(),
      snippet,
      mode: 'merge',
    });
    const jobId = response.data.job_id;
    setPreviewJobId(jobId);
    const result = await api.get<{ diffs: Record<string, { diff: string }> }>(`/jobs/${jobId}/results`);
    setDiffs(result.data.diffs || {});
    setLoading(false);
  };

  const handleCommit = async () => {
    if (!previewJobId) return;
    const response = await api.post('/automation/deploy/commit', {
      previous_job_id: previewJobId,
      confirm: true,
    });
    navigate(`/jobs/${response.data.job_id}`);
  };

  return (
    <section>
      <h2>Config deployment</h2>
      <p>Preview diffs before committing to the network.</p>
      <form onSubmit={handlePreview} style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxWidth: 700 }}>
        <label>
          Device IDs
          <input value={deviceIds} onChange={(e) => setDeviceIds(e.target.value)} placeholder="Leave empty for all" />
        </label>
        <label>
          Config snippet
          <textarea rows={8} value={snippet} onChange={(e) => setSnippet(e.target.value)} />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? 'Previewing...' : 'Preview changes'}
        </button>
      </form>
      {previewJobId && (
        <article style={{ marginTop: '2rem' }}>
          <h3>Preview results (job #{previewJobId})</h3>
          {Object.entries(diffs).map(([host, payload]) => (
            <details key={host} style={{ marginBottom: '1rem' }}>
              <summary>{host}</summary>
              <pre>{payload.diff || 'No change detected'}</pre>
            </details>
          ))}
          <button type="button" onClick={handleCommit} disabled={!Object.keys(diffs).length}>
            Commit changes
          </button>
        </article>
      )}
    </section>
  );
};

export default ConfigDeployPage;
