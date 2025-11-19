import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { JobLogEntry, JobSummary, createHttpClient } from '../../api/http';

interface Props {
  token: string;
}

const JobDetailPage = ({ token }: Props) => {
  const { jobId } = useParams();
  const api = useMemo(() => createHttpClient(token), [token]);
  const [job, setJob] = useState<JobSummary | null>(null);
  const [logs, setLogs] = useState<JobLogEntry[]>([]);
  const [result, setResult] = useState<Record<string, unknown>>({});

  useEffect(() => {
    if (!jobId) return;
    const load = async () => {
      const jobResponse = await api.get<JobSummary>(`/jobs/${jobId}`);
      setJob(jobResponse.data);
      const logResponse = await api.get<JobLogEntry[]>(`/jobs/${jobId}/logs`);
      setLogs(logResponse.data);
      const resultResponse = await api.get<Record<string, unknown>>(`/jobs/${jobId}/results`);
      setResult(resultResponse.data);
    };
    load();
  }, [api, jobId]);

  useEffect(() => {
    if (!jobId) return;
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/jobs/${jobId}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setLogs((prev) => [...prev, data]);
    };
    return () => ws.close();
  }, [jobId]);

  if (!job) {
    return <p>Loading job...</p>;
  }

  return (
    <section>
      <header>
        <h2>Job #{job.id}</h2>
        <p>{job.type} — {job.status}</p>
      </header>
      <article>
        <h3>Targets</h3>
        <pre>{JSON.stringify(job.target_summary ?? {}, null, 2)}</pre>
      </article>
      <article>
        <h3>Result summary</h3>
        <pre>{JSON.stringify(result, null, 2)}</pre>
      </article>
      <article>
        <h3>Live logs</h3>
        <div style={{ maxHeight: 300, overflowY: 'auto', background: '#0f172a', color: '#e2e8f0', padding: '1rem' }}>
          {logs.map((log, idx) => (
            <div key={`${log.ts}-${idx}`}>
              <strong>[{log.level}]</strong> {log.host ? `${log.host}:` : ''} {log.message}
            </div>
          ))}
        </div>
      </article>
    </section>
  );
};

export default JobDetailPage;
