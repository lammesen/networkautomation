import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { JobSummary, createHttpClient } from '../../api/http';

interface Props {
  token: string;
}

const JobsPage = ({ token }: Props) => {
  const api = useMemo(() => createHttpClient(token), [token]);
  const [jobs, setJobs] = useState<JobSummary[]>([]);

  useEffect(() => {
    const load = async () => {
      const response = await api.get<JobSummary[]>('/jobs');
      setJobs(response.data);
    };
    load();
  }, [api]);

  return (
    <section>
      <header>
        <h2>Jobs</h2>
        <p>Track automation workflows end-to-end.</p>
      </header>
      <table style={{ width: '100%', marginTop: '1rem' }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Type</th>
            <th>Status</th>
            <th>Requested</th>
            <th>Finished</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((job) => (
            <tr key={job.id}>
              <td><Link to={`/jobs/${job.id}`}>#{job.id}</Link></td>
              <td>{job.type}</td>
              <td>{job.status}</td>
              <td>{new Date(job.requested_at).toLocaleString()}</td>
              <td>{job.finished_at ? new Date(job.finished_at).toLocaleString() : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
};

export default JobsPage;
