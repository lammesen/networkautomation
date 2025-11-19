import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { apiClient } from '../api/client'

export default function CommandsPage() {
  const [targets, setTargets] = useState({ site: '', role: '', vendor: '' })
  const [commands, setCommands] = useState('')
  const [result, setResult] = useState<any>(null)

  const runCommandsMutation = useMutation({
    mutationFn: (data: any) => apiClient.runCommands(data),
    onSuccess: (data) => {
      setResult({ success: true, job_id: data.job_id })
    },
    onError: (error: any) => {
      setResult({ success: false, error: error.message })
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    const commandList = commands.split('\n').filter(cmd => cmd.trim())
    const targetFilters: any = {}
    
    if (targets.site) targetFilters.site = targets.site
    if (targets.role) targetFilters.role = targets.role
    if (targets.vendor) targetFilters.vendor = targets.vendor
    
    runCommandsMutation.mutate({
      targets: targetFilters,
      commands: commandList,
    })
  }

  return (
    <div>
      <h1 style={{ marginBottom: '1rem' }}>Run Commands</h1>
      
      <form onSubmit={handleSubmit} style={{ maxWidth: '800px' }}>
        {/* Target Selection */}
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          marginBottom: '1.5rem'
        }}>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.125rem', fontWeight: '600' }}>
            Target Devices
          </h2>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                Site
              </label>
              <input
                type="text"
                value={targets.site}
                onChange={(e) => setTargets({ ...targets, site: e.target.value })}
                placeholder="e.g., dc1"
                style={{ 
                  width: '100%', 
                  padding: '0.5rem', 
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              />
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                Role
              </label>
              <input
                type="text"
                value={targets.role}
                onChange={(e) => setTargets({ ...targets, role: e.target.value })}
                placeholder="e.g., edge"
                style={{ 
                  width: '100%', 
                  padding: '0.5rem', 
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              />
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>
                Vendor
              </label>
              <input
                type="text"
                value={targets.vendor}
                onChange={(e) => setTargets({ ...targets, vendor: e.target.value })}
                placeholder="e.g., cisco"
                style={{ 
                  width: '100%', 
                  padding: '0.5rem', 
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              />
            </div>
          </div>
          
          <p style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: '#6b7280' }}>
            Leave filters empty to target all enabled devices
          </p>
        </div>

        {/* Commands Input */}
        <div style={{ 
          backgroundColor: 'white', 
          padding: '1.5rem', 
          borderRadius: '8px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          marginBottom: '1.5rem'
        }}>
          <h2 style={{ marginBottom: '1rem', fontSize: '1.125rem', fontWeight: '600' }}>
            Commands
          </h2>
          
          <textarea
            value={commands}
            onChange={(e) => setCommands(e.target.value)}
            placeholder="Enter commands, one per line:&#10;show version&#10;show ip interface brief&#10;show running-config | include hostname"
            required
            rows={8}
            style={{ 
              width: '100%', 
              padding: '0.75rem', 
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '0.875rem'
            }}
          />
          
          <p style={{ marginTop: '0.75rem', fontSize: '0.875rem', color: '#6b7280' }}>
            Commands will be executed on all matching devices in parallel
          </p>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={runCommandsMutation.isPending}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: runCommandsMutation.isPending ? '#9ca3af' : '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            fontWeight: '500',
            cursor: runCommandsMutation.isPending ? 'not-allowed' : 'pointer',
          }}
        >
          {runCommandsMutation.isPending ? 'Submitting...' : 'Run Commands'}
        </button>
      </form>

      {/* Result */}
      {result && (
        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          backgroundColor: result.success ? '#d1fae5' : '#fee2e2',
          color: result.success ? '#065f46' : '#991b1b',
          borderRadius: '8px',
          maxWidth: '800px'
        }}>
          {result.success ? (
            <div>
              <strong>✓ Job Created Successfully</strong>
              <p style={{ marginTop: '0.5rem' }}>Job ID: {result.job_id}</p>
              <p style={{ marginTop: '0.5rem', fontSize: '0.875rem' }}>
                Go to the Jobs page to monitor progress
              </p>
            </div>
          ) : (
            <div>
              <strong>✗ Error</strong>
              <p style={{ marginTop: '0.5rem' }}>{result.error}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
