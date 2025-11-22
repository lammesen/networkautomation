import { useEffect, useMemo, useRef, useState } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'
import { Device } from '../types'
import { useAuthStore } from '@/store/authStore'

type MessageRole = 'system' | 'user' | 'device' | 'error'

interface Message {
  id: string
  role: MessageRole
  text: string
}

type SSHWebsocketEvent =
  | {
      type: 'connected'
      device_id: number
      device_name: string
      prompt?: string
      session_id?: string
    }
  | { type: 'command_ack'; command: string }
  | { type: 'output'; command: string; stdout?: string; stderr?: string; exit_status?: number }
  | { type: 'error'; detail?: string }
  | { type: 'closed'; reason?: string }
  | { type: 'keepalive'; ts?: string }

interface DeviceTerminalDialogProps {
  open: boolean
  device: Device | null
  onClose: () => void
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

function buildWsUrl(deviceId: number, token: string, customerId?: number | null): string {
  const url = new URL(API_BASE_URL)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'

  const basePath = url.pathname.replace(/\/$/, '')
  url.pathname = `${basePath}/ws/devices/${deviceId}/ssh`
  url.searchParams.set('token', token)
  if (customerId) {
    url.searchParams.set('customer_id', String(customerId))
  }
  return url.toString()
}

export function DeviceTerminalDialog({ open, device, onClose }: DeviceTerminalDialogProps) {
  const { token, activeCustomerId } = useAuthStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [status, setStatus] = useState<'idle' | 'connecting' | 'connected' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const wsUrl = useMemo(() => {
    if (!device || !token) return null
    try {
      return buildWsUrl(device.id, token, activeCustomerId)
    } catch (err) {
      console.error(err)
      return null
    }
  }, [device, token, activeCustomerId])

  useEffect(() => {
    setTimeout(() => {
      if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight
      }
    }, 10)
  }, [messages])

  useEffect(() => {
    if (!open || !device) {
      return
    }

    if (!token) {
      setError('Authentication required to open terminal')
      setStatus('error')
      return
    }

    if (!wsUrl) {
      setError('Unable to build websocket URL')
      setStatus('error')
      return
    }

    setMessages([])
    setStatus('connecting')
    setError(null)

    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('connected')
      addMessage('system', 'Connection established. Type commands below.')
    }

    ws.onclose = (evt) => {
      if (evt.code !== 1000) {
        addMessage('error', evt.reason || 'Connection closed')
        setError(evt.reason || 'Connection closed')
        setStatus('error')
      } else {
        addMessage('system', 'Connection closed')
        setStatus('idle')
      }
    }

    ws.onerror = () => {
      setError('WebSocket error')
      setStatus('error')
    }

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as SSHWebsocketEvent
        handleServerEvent(payload)
      } catch (err) {
        console.error('Failed to parse websocket message', err)
      }
    }

    return () => {
      ws.close()
      wsRef.current = null
      setStatus('idle')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, device?.id, wsUrl, token])

  const addMessage = (role: MessageRole, text: string) => {
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`,
        role,
        text,
      },
    ])
  }

  const handleServerEvent = (payload: SSHWebsocketEvent) => {
    if (payload.type === 'connected') {
      addMessage('system', `Connected to ${payload.device_name} (${payload.prompt?.trim() || 'session'})`)
      return
    }

    if (payload.type === 'command_ack') {
      addMessage('system', `Running: ${payload.command}`)
      return
    }

    if (payload.type === 'output') {
      if (payload.stdout) {
        addMessage('device', payload.stdout)
      }
      if (payload.stderr) {
        addMessage('error', payload.stderr)
      }
      if (typeof payload.exit_status === 'number') {
        addMessage('system', `Exit status: ${payload.exit_status}`)
      }
      return
    }

    if (payload.type === 'error') {
      addMessage('error', payload.detail || 'Unknown error')
      toast.error(payload.detail || 'Terminal error')
      setStatus('error')
      return
    }

    if (payload.type === 'closed') {
      addMessage('system', payload.reason || 'Session closed')
      setStatus('idle')
      return
    }

    if (payload.type === 'keepalive') {
      return
    }

    addMessage('system', `Event: ${JSON.stringify(payload)}`)
  }

  const sendCommand = (command: string) => {
    if (!command.trim()) return
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error('Terminal not connected')
      return
    }
    addMessage('user', command)
    wsRef.current.send(JSON.stringify({ type: 'command', command }))
  }

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    sendCommand(input)
    setInput('')
  }

  const connectionBadge = (() => {
    if (status === 'connected') {
      return <Badge variant="default">Connected</Badge>
    }
    if (status === 'connecting') {
      return <Badge variant="secondary">Connecting…</Badge>
    }
    if (status === 'error') {
      return <Badge variant="destructive">Error</Badge>
    }
    return <Badge variant="outline">Idle</Badge>
  })()

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Device Terminal</DialogTitle>
          <DialogDescription>
            {device ? `${device.hostname} (${device.mgmt_ip})` : 'Select a device to start a terminal session.'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <span className="font-medium">Status:</span>
            {connectionBadge}
          </div>
          {error ? <span className="text-destructive text-sm">{error}</span> : null}
        </div>

        <ScrollArea className="h-72 rounded-md border p-3" ref={scrollRef as any}>
          <div className="space-y-2">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`text-sm whitespace-pre-wrap ${
                  message.role === 'user'
                    ? 'text-blue-600'
                    : message.role === 'device'
                      ? 'text-foreground'
                      : message.role === 'error'
                        ? 'text-destructive'
                        : 'text-muted-foreground'
                }`}
              >
                {message.role === 'user' ? `› ${message.text}` : message.text}
              </div>
            ))}
            {messages.length === 0 ? (
              <div className="text-muted-foreground text-sm">Output will appear here once the session starts.</div>
            ) : null}
          </div>
        </ScrollArea>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={status === 'connected' ? 'Enter a command (e.g. show version)' : 'Waiting for connection…'}
            disabled={status !== 'connected'}
            autoComplete="off"
          />
          <Button type="submit" disabled={status !== 'connected'}>
            Send
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  )
}

