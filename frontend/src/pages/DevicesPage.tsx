import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useState } from 'react'

export default function DevicesPage() {
  const [siteFilter, setSiteFilter] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [search, setSearch] = useState('')
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['devices', siteFilter, roleFilter, search],
    queryFn: () => apiClient.getDevices({ site: siteFilter, role: roleFilter, search }),
  })

  if (isLoading) return <div>Loading devices...</div>
  if (error) return <div style={{ color: 'red' }}>Error loading devices</div>

  return (
    <div>
      <h1 style={{ marginBottom: '1rem' }}>Devices</h1>
      
      {/* Filters */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <input
          type="text"
          placeholder="Search hostname or IP..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ padding: '0.5rem', minWidth: '200px', border: '1px solid #ddd', borderRadius: '4px' }}
        />
        <input
          type="text"
          placeholder="Filter by site..."
          value={siteFilter}
          onChange={(e) => setSiteFilter(e.target.value)}
          style={{ padding: '0.5rem', minWidth: '150px', border: '1px solid #ddd', borderRadius: '4px' }}
        />
        <input
          type="text"
          placeholder="Filter by role..."
          value={roleFilter}
          onChange={(e) => setRoleFilter(e.target.value)}
          style={{ padding: '0.5rem', minWidth: '150px', border: '1px solid #ddd', borderRadius: '4px' }}
        />
      </div>

      {/* Device Table */}
      <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Hostname</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>IP Address</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Vendor</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Platform</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Role</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Site</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {data?.devices && data.devices.length > 0 ? (
              data.devices.map((device: any) => (
                <tr key={device.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '0.75rem' }}>{device.hostname}</td>
                  <td style={{ padding: '0.75rem' }}>{device.mgmt_ip}</td>
                  <td style={{ padding: '0.75rem' }}>{device.vendor}</td>
                  <td style={{ padding: '0.75rem' }}>{device.platform}</td>
                  <td style={{ padding: '0.75rem' }}>{device.role || '-'}</td>
                  <td style={{ padding: '0.75rem' }}>{device.site || '-'}</td>
                  <td style={{ padding: '0.75rem' }}>
                    <span style={{
                      padding: '0.25rem 0.5rem',
                      borderRadius: '4px',
                      fontSize: '0.875rem',
                      backgroundColor: device.enabled ? '#d1fae5' : '#fee2e2',
                      color: device.enabled ? '#065f46' : '#991b1b',
                    }}>
                      {device.enabled ? 'Enabled' : 'Disabled'}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={7} style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
                  No devices found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Summary */}
      {data?.total !== undefined && (
        <div style={{ marginTop: '1rem', color: '#6b7280' }}>
          Total devices: {data.total}
        </div>
      )}
    </div>
  )
}
