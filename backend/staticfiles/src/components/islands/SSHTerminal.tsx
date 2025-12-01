/**
 * SSHTerminal - React island for interactive SSH terminal using xterm.js
 * Connects to WebSocket at /ws/devices/{deviceId}/ssh/
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import { Button } from "@/components/ui/button";

interface SSHTerminalProps {
  deviceId: number;
  hostname: string;
}

type ConnectionState = "disconnected" | "connecting" | "connected" | "error";

interface SSHMessage {
  type: "connected" | "output" | "error" | "keepalive";
  device_id?: number;
  hostname?: string;
  command?: string;
  stdout?: string;
  stderr?: string;
  exit_status?: number;
  detail?: string;
}

export function SSHTerminal({ deviceId, hostname }: SSHTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const inputBufferRef = useRef<string>("");

  const [connectionState, setConnectionState] =
    useState<ConnectionState>("disconnected");
  const [isExpanded, setIsExpanded] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string>("");

  const prompt = `${hostname}# `;

  const writePrompt = useCallback(() => {
    if (termRef.current) {
      termRef.current.write(`\r\n${prompt}`);
    }
  }, [prompt]);

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data: SSHMessage = JSON.parse(event.data);

        switch (data.type) {
          case "connected":
            setConnectionState("connected");
            if (termRef.current) {
              termRef.current.writeln(
                `\x1b[32mConnected to ${data.hostname}\x1b[0m`
              );
              termRef.current.write(prompt);
            }
            break;

          case "output":
            if (termRef.current) {
              // Write stdout
              if (data.stdout) {
                const lines = data.stdout.split("\n");
                lines.forEach((line, idx) => {
                  if (idx > 0) termRef.current!.write("\r\n");
                  termRef.current!.write(line);
                });
              }
              // Write stderr in red
              if (data.stderr) {
                const lines = data.stderr.split("\n");
                lines.forEach((line, idx) => {
                  if (idx > 0) termRef.current!.write("\r\n");
                  termRef.current!.write(`\x1b[31m${line}\x1b[0m`);
                });
              }
              writePrompt();
            }
            break;

          case "error":
            if (termRef.current) {
              termRef.current.writeln(`\r\n\x1b[31mError: ${data.detail}\x1b[0m`);
              writePrompt();
            }
            break;

          case "keepalive":
            // Ignore keepalive messages
            break;
        }
      } catch (e) {
        console.error("Failed to parse SSH message:", e);
      }
    },
    [prompt, writePrompt]
  );

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setConnectionState("connecting");
    setErrorMessage("");

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/devices/${deviceId}/ssh/`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      // Connection state will be set to 'connected' when we receive the connected message
    };

    ws.onmessage = handleMessage;

    ws.onerror = () => {
      setConnectionState("error");
      setErrorMessage("WebSocket connection failed");
    };

    ws.onclose = (event) => {
      setConnectionState("disconnected");
      wsRef.current = null;

      if (termRef.current) {
        const closeReasons: Record<number, string> = {
          4001: "Authentication required",
          4002: "Invalid device ID",
          4003: "Access denied",
          4004: "Device not found",
          4005: "No credentials configured for device",
        };
        const reason = closeReasons[event.code] || `Connection closed (${event.code})`;
        termRef.current.writeln(`\r\n\x1b[33m${reason}\x1b[0m`);
      }
    };
  }, [deviceId, handleMessage]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnectionState("disconnected");
  }, []);

  const sendCommand = useCallback((command: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "command", command }));
    }
  }, []);

  const handleTerminalData = useCallback(
    (data: string) => {
      if (connectionState !== "connected" || !termRef.current) return;

      for (const char of data) {
        if (char === "\r" || char === "\n") {
          // Enter pressed - send command
          const command = inputBufferRef.current.trim();
          termRef.current.write("\r\n");
          if (command) {
            sendCommand(command);
          } else {
            termRef.current.write(prompt);
          }
          inputBufferRef.current = "";
        } else if (char === "\x7f" || char === "\b") {
          // Backspace
          if (inputBufferRef.current.length > 0) {
            inputBufferRef.current = inputBufferRef.current.slice(0, -1);
            termRef.current.write("\b \b");
          }
        } else if (char === "\x03") {
          // Ctrl+C - cancel current input
          inputBufferRef.current = "";
          termRef.current.write("^C");
          writePrompt();
        } else if (char === "\x15") {
          // Ctrl+U - clear line
          const len = inputBufferRef.current.length;
          inputBufferRef.current = "";
          termRef.current.write("\b \b".repeat(len));
        } else if (char >= " " && char <= "~") {
          // Printable character
          inputBufferRef.current += char;
          termRef.current.write(char);
        }
      }
    },
    [connectionState, sendCommand, prompt, writePrompt]
  );

  // Initialize terminal when expanded
  useEffect(() => {
    if (!isExpanded || !terminalRef.current || termRef.current) return;

    const term = new Terminal({
      cursorBlink: true,
      fontSize: 14,
      fontFamily: 'Menlo, Monaco, "Courier New", monospace',
      theme: {
        background: "#1a1b26",
        foreground: "#c0caf5",
        cursor: "#c0caf5",
        cursorAccent: "#1a1b26",
        selectionBackground: "#33467c",
        black: "#15161e",
        red: "#f7768e",
        green: "#9ece6a",
        yellow: "#e0af68",
        blue: "#7aa2f7",
        magenta: "#bb9af7",
        cyan: "#7dcfff",
        white: "#a9b1d6",
        brightBlack: "#414868",
        brightRed: "#f7768e",
        brightGreen: "#9ece6a",
        brightYellow: "#e0af68",
        brightBlue: "#7aa2f7",
        brightMagenta: "#bb9af7",
        brightCyan: "#7dcfff",
        brightWhite: "#c0caf5",
      },
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.open(terminalRef.current);

    // Delay fit to ensure container has rendered
    setTimeout(() => {
      fitAddon.fit();
    }, 0);

    term.onData(handleTerminalData);

    termRef.current = term;
    fitAddonRef.current = fitAddon;

    term.writeln(`\x1b[36mSSH Terminal for ${hostname}\x1b[0m`);
    term.writeln('Type commands and press Enter. Use "exit" to disconnect.');
    term.writeln("");

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
      }
    });
    resizeObserver.observe(terminalRef.current);

    return () => {
      resizeObserver.disconnect();
      term.dispose();
      termRef.current = null;
      fitAddonRef.current = null;
    };
  }, [isExpanded, hostname, handleTerminalData]);

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Re-fit terminal when expanded state changes
  useEffect(() => {
    if (isExpanded && fitAddonRef.current) {
      setTimeout(() => {
        fitAddonRef.current?.fit();
      }, 100);
    }
  }, [isExpanded]);

  const getStatusColor = () => {
    switch (connectionState) {
      case "connected":
        return "bg-green-500";
      case "connecting":
        return "bg-yellow-500 animate-pulse";
      case "error":
        return "bg-red-500";
      default:
        return "bg-gray-400";
    }
  };

  const getStatusText = () => {
    switch (connectionState) {
      case "connected":
        return "Connected";
      case "connecting":
        return "Connecting...";
      case "error":
        return errorMessage || "Error";
      default:
        return "Disconnected";
    }
  };

  return (
    <div className="rounded-lg border bg-card">
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-5 w-5 text-primary"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <h2 className="font-semibold">SSH Terminal</h2>
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${getStatusColor()}`} />
            <span className="text-sm text-muted-foreground">
              {getStatusText()}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isExpanded && (
            <div onClick={(e) => e.stopPropagation()}>
              {connectionState === "disconnected" ||
              connectionState === "error" ? (
                <Button size="sm" onClick={connect}>
                  Connect
                </Button>
              ) : connectionState === "connected" ? (
                <Button size="sm" variant="outline" onClick={disconnect}>
                  Disconnect
                </Button>
              ) : (
                <Button size="sm" disabled>
                  Connecting...
                </Button>
              )}
            </div>
          )}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className={`h-5 w-5 text-muted-foreground transition-transform ${
              isExpanded ? "rotate-180" : ""
            }`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </div>

      {/* Terminal Container */}
      {isExpanded && (
        <div className="border-t">
          <div
            ref={terminalRef}
            className="h-80 bg-[#1a1b26] p-2"
            style={{ minHeight: "320px" }}
          />
        </div>
      )}
    </div>
  );
}

export default SSHTerminal;
