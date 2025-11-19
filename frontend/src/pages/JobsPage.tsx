import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../api/client'
import { useState } from 'react'

export default function JobsPage() {
  const [statusFilter, setStatusFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  
  const { data, isLoading, error } = useQuery({
    queryKey: ['jobs', statusFilter, typeFilter],
    queryFn: () => apiClient.getJobs({ status: statusFilter, type: typeFilter }),
  })

  if (isLoading) return <div>Loading jobs...</div>
  if (error) return <div style={{ color: 'red' }}>Error loading jobs</div>

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return { bg: '#d1fae5', color: '#065f46' }
      case 'running':
        return { bg: '#dbeafe', color: '#1e40af' }
      case 'failed':
        return { bg: '#fee2e2', color: '#991b1b' }
      case 'partial':
        return { bg: '#fef3c7', color: '#92400e' }
      default:
        return { bg: '#f3f4f6', color: '#374151' }
    }
  }

  return (
    <div>
      <h1 style={{ marginBottom: '1rem' }}>Jobs</h1>
      
      {/* Filters */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '1rem' }}>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
        >
          <option value="">All Statuses</option>
          <option value="queued">Queued</option>
          <option value="running">Running</option>
          <option value="success">Success</option>
          <option value="partial">Partial</option>
          <option value="failed">Failed</option>
        </select>
        
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{ padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px' }}
        >
          <option value="">All Types</option>
          <option value="run_commands">Run Commands</option>
          <option value="config_backup">Config Backup</option>
          <option value="config_deploy_preview">Config Deploy Preview</option>
          <option value="config_deploy_commit">Config Deploy Commit</option>
          <option value="compliance_check">Compliance Check</option>
        </select>
      </div>

      {/* Jobs Table */}
      <div style={{ backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>ID</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Type</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Status</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Started</th>
              <th style={{ padding: '0.75rem', textAlign: 'left', fontWeight: '600' }}>Finished</th>
            </tr>
          </thead>
          <tbody>
            {data && data.length > 0 ? (
              data.map((job: any) => {
                const statusStyle = getStatusColor(job.status)
                return (
                  <tr key={job.id} style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <td style={{ padding: '0.75rem' }}>#{job.id}</td>
                    <td style={{ padding: '0.75rem' }}>
                      {job.type.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase())}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      <span style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.875rem',
                        backgroundColor: statusStyle.bg,
                        color: statusStyle.color,
                      }}>
                        {job.status}
                      </span>
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {job.started_at ? new Date(job.started_at).toLocaleString() : '-'}
                    </td>
                    <td style={{ padding: '0.75rem' }}>
                      {job.finished_at ? new Date(job.finished_at).toLocaleString() : '-'}
                    </td>
                  </tr>
                )
              })
            ) : (
              <tr>
                <td colSpan={5} style={{ padding: '2rem', textAlign: 'center', color: '#6b7280' }}>
                  No jobs found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
