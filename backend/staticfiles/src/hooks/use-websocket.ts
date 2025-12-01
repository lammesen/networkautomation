import { useEffect, useRef, useCallback, useState } from "react";

export type WebSocketMessage = {
  type: string;
  entity?: string;
  id?: number | string;
  status?: string;
  data?: Record<string, unknown>;
};

export type WebSocketStatus = "connecting" | "connected" | "disconnected" | "error";

type UseWebSocketOptions = {
  /** URL path for WebSocket connection (default: /ws/updates/) */
  path?: string;
  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;
  /** Max reconnection attempts (default: 10) */
  maxReconnectAttempts?: number;
  /** Reconnection delay in ms (default: 3000) */
  reconnectDelay?: number;
  /** Filter messages by entity type */
  entityFilter?: string | string[];
  /** Callback when a message is received */
  onMessage?: (message: WebSocketMessage) => void;
  /** Callback when connection status changes */
  onStatusChange?: (status: WebSocketStatus) => void;
};

/**
 * Hook for managing WebSocket connection to the Django backend
 * Provides real-time updates for entities (jobs, devices, compliance, etc.)
 */
export function useWebSocket(options: UseWebSocketOptions = {}) {
  const {
    path = "/ws/updates/",
    autoReconnect = true,
    maxReconnectAttempts = 10,
    reconnectDelay = 3000,
    entityFilter,
    onMessage,
    onStatusChange,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>("disconnected");
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  const updateStatus = useCallback(
    (newStatus: WebSocketStatus) => {
      setStatus(newStatus);
      onStatusChange?.(newStatus);
    },
    [onStatusChange]
  );

  const connect = useCallback(() => {
    // Build WebSocket URL
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.host}${path}`;

    updateStatus("connecting");

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectAttemptsRef.current = 0;
      updateStatus("connected");
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        // Filter by entity if specified
        if (entityFilter && message.entity) {
          const filters = Array.isArray(entityFilter) ? entityFilter : [entityFilter];
          if (!filters.includes(message.entity)) {
            return;
          }
        }

        setLastMessage(message);
        onMessage?.(message);

        // Dispatch global event for non-React listeners
        const customEvent = new CustomEvent("webnet:update", { detail: message });
        document.dispatchEvent(customEvent);
      } catch (error) {
        console.error("Failed to parse WebSocket message:", error);
      }
    };

    ws.onclose = (event) => {
      wsRef.current = null;
      updateStatus("disconnected");

      // Attempt reconnection if not a clean close
      if (
        autoReconnect &&
        event.code !== 1000 &&
        reconnectAttemptsRef.current < maxReconnectAttempts
      ) {
        reconnectAttemptsRef.current++;
        reconnectTimeoutRef.current = setTimeout(connect, reconnectDelay);
      }
    };

    ws.onerror = () => {
      updateStatus("error");
    };
  }, [
    path,
    autoReconnect,
    maxReconnectAttempts,
    reconnectDelay,
    entityFilter,
    onMessage,
    updateStatus,
  ]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close(1000);
      wsRef.current = null;
    }
    updateStatus("disconnected");
  }, [updateStatus]);

  const send = useCallback((data: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    status,
    lastMessage,
    send,
    connect,
    disconnect,
    isConnected: status === "connected",
  };
}

/**
 * Hook for subscribing to specific entity updates
 * Automatically calls the callback when matching updates arrive
 */
export function useEntityUpdates(
  entityType: string | string[],
  callback: (message: WebSocketMessage) => void
) {
  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<WebSocketMessage>;
      const message = customEvent.detail;

      const types = Array.isArray(entityType) ? entityType : [entityType];
      if (message.entity && types.includes(message.entity)) {
        callback(message);
      }
    };

    document.addEventListener("webnet:update", handler);
    return () => document.removeEventListener("webnet:update", handler);
  }, [entityType, callback]);
}

export default useWebSocket;
