import { useEffect, useRef, useState, useMemo } from 'react'
import { useAuthStore } from '@/store/authStore'
import type { LiveLogEntry } from '../types'

interface UseJobWebSocketOptions {
  jobId: number | null
  enabled: boolean
}

interface UseJobWebSocketReturn {
  logs: LiveLogEntry[]
  status: string | null
  isConnected: boolean
  clearLogs: () => void
}

/**
 * Hook to connect to job WebSocket for live logs and status updates
 */
export function useJobWebSocket({ jobId, enabled }: UseJobWebSocketOptions): UseJobWebSocketReturn {
  const [logs, setLogs] = useState<LiveLogEntry[]>([])
  const [status, setStatus] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const token = useAuthStore((s) => s.token)

  const wsBase = useMemo(() => {
    const api = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'
    return api.replace(/^http/, 'ws')
  }, [])

  useEffect(() => {
    if (!enabled || !jobId) {
      return
    }

    const url = `${wsBase}/ws/jobs/${jobId}?token=${encodeURIComponent(token || '')}`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setIsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'status') {
          setStatus(msg.status)
        } else if (msg.type === 'log') {
          setLogs((prev) => [...prev, { ts: msg.ts, level: msg.level, message: msg.message, host: msg.host }])
        } else if (msg.type === 'complete') {
          setStatus(msg.status)
        }
      } catch {
        // Ignore parse errors
      }
    }

    ws.onerror = () => {
      setLogs((prev) => [...prev, { ts: new Date().toISOString(), level: 'ERROR', message: 'WebSocket error' }])
    }

    ws.onclose = () => {
      setIsConnected(false)
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [enabled, jobId, wsBase, token])

  const clearLogs = () => {
    setLogs([])
    setStatus(null)
  }

  // Sort logs by timestamp
  const sortedLogs = useMemo(
    () => [...logs].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime()),
    [logs]
  )

  return {
    logs: sortedLogs,
    status,
    isConnected,
    clearLogs,
  }
}
