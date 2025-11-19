import { useEffect, useMemo, useState } from 'react';
import { createHttpClient, CompliancePolicy } from '../../api/http';

interface Props {
  token: string;
}

interface ComplianceResultRow {
  id: number;
  device_id: number;
  status: string;
  ts: string;
}

const CompliancePage = ({ token }: Props) => {
  const api = useMemo(() => createHttpClient(token), [token]);
  const [policies, setPolicies] = useState<CompliancePolicy[]>([]);
  const [selectedPolicyId, setSelectedPolicyId] = useState<number | null>(null);
  const [results, setResults] = useState<ComplianceResultRow[]>([]);

  useEffect(() => {
    const loadPolicies = async () => {
      const response = await api.get<CompliancePolicy[]>('/compliance/policies');
      setPolicies(response.data);
      if (response.data.length) {
        setSelectedPolicyId(response.data[0].id);
      }
    };
    loadPolicies();
  }, [api]);

  useEffect(() => {
    if (!selectedPolicyId) return;
    const loadResults = async () => {
      const response = await api.get<ComplianceResultRow[]>(`/compliance/results`, {
        params: { policy_id: selectedPolicyId },
      });
      setResults(response.data);
    };
    loadResults();
  }, [api, selectedPolicyId]);

  const handleRun = async (policyId: number) => {
    await api.post('/automation/compliance', {
      policy_id: policyId,
      targets: { device_ids: [] },
    });
    alert('Compliance job dispatched. Check Jobs page for details.');
  };

  return (
    <section>
      <h2>Compliance policies</h2>
      <div style={{ display: 'flex', gap: '2rem' }}>
        <div style={{ flex: 1 }}>
          <h3>Policies</h3>
          <ul>
            {policies.map((policy) => (
              <li key={policy.id}>
                <button type="button" onClick={() => setSelectedPolicyId(policy.id)}>
                  {policy.name}
                </button>
                <button type="button" onClick={() => handleRun(policy.id)} style={{ marginLeft: '0.5rem' }}>
                  Run now
                </button>
              </li>
            ))}
          </ul>
        </div>
        <div style={{ flex: 2 }}>
          <h3>Results</h3>
          {selectedPolicyId ? (
            <table style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Device</th>
                  <th>Status</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {results.map((result) => (
                  <tr key={result.id}>
                    <td>{result.id}</td>
                    <td>{result.device_id}</td>
                    <td>{result.status}</td>
                    <td>{new Date(result.ts).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p>Select a policy to view results.</p>
          )}
        </div>
      </div>
    </section>
  );
};

export default CompliancePage;
