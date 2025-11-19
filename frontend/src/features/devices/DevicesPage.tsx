import { FormEvent, useEffect, useMemo, useState } from 'react';
import { createHttpClient, Device } from '../../api/http';

interface Props {
  token: string;
}

const DevicesPage = ({ token }: Props) => {
  const api = useMemo(() => createHttpClient(token), [token]);
  const [devices, setDevices] = useState<Device[]>([]);
  const [search, setSearch] = useState('');

  const fetchDevices = async (query?: string) => {
    const response = await api.get<Device[]>('/devices', { params: query ? { search: query } : {} });
    setDevices(response.data);
  };

  useEffect(() => {
    fetchDevices();
  }, [api]);

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    fetchDevices(search);
  };

  return (
    <section>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2>Devices</h2>
          <p>Inventory managed directly from the API.</p>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '0.5rem' }}>
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search hostname or IP" />
          <button type="submit">Filter</button>
        </form>
      </header>
      <table style={{ width: '100%', marginTop: '1rem' }}>
        <thead>
          <tr>
            <th>Hostname</th>
            <th>IP</th>
            <th>Vendor</th>
            <th>Role</th>
            <th>Site</th>
            <th>Tags</th>
          </tr>
        </thead>
        <tbody>
          {devices.map((device) => (
            <tr key={device.id}>
              <td>{device.hostname}</td>
              <td>{device.mgmt_ip}</td>
              <td>{device.vendor || '-'}</td>
              <td>{device.role || '-'}</td>
              <td>{device.site || '-'}</td>
              <td>{device.tags || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
};

export default DevicesPage;
