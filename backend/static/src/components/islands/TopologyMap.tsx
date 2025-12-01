import { useCallback, useEffect, useRef, useState } from "react";
import { Network, Options, Data } from "vis-network/standalone";
import { DataSet } from "vis-data/standalone";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Popover, PopoverContent, PopoverTrigger } from "../ui/popover";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Search,
  X,
  RefreshCw,
  Router,
  Server,
  Shield,
  Box,
  HelpCircle,
  MonitorSmartphone,
  Wifi,
} from "lucide-react";

// Types for the topology data
type NodeData = {
  hostname: string;
  mgmt_ip: string | null;
  vendor: string | null;
  platform: string | null;
  site: string | null;
  role: string | null;
  enabled: boolean | null;
  reachability_status: string | null;
  detail_url: string | null;
};

type EdgeData = {
  local_interface: string;
  remote_interface: string;
  protocol: string;
  discovered_at: string;
};

type TopologyNode = {
  id: string;
  label: string;
  data: NodeData;
  type: "device" | "unknown";
};

type TopologyEdge = {
  id: string;
  source: string;
  target: string;
  data: EdgeData;
};

type TopologyMapProps = {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  onRefresh?: () => void;
  wsUrl?: string;
};

// Color scheme based on device status
const STATUS_COLORS = {
  reachable: "#22c55e", // green-500
  unreachable: "#ef4444", // red-500
  unknown: "#6b7280", // gray-500
  disabled: "#f59e0b", // amber-500
} as const;

// Get node color based on status
function getNodeColor(node: TopologyNode): string {
  if (node.type === "unknown") return STATUS_COLORS.unknown;
  if (node.data.enabled === false) return STATUS_COLORS.disabled;
  
  const status = node.data.reachability_status?.toLowerCase();
  if (status === "reachable" || status === "up") return STATUS_COLORS.reachable;
  if (status === "unreachable" || status === "down") return STATUS_COLORS.unreachable;
  return STATUS_COLORS.unknown;
}

// Get icon based on device role
function getRoleIcon(role: string | null): React.ReactNode {
  const iconClass = "h-4 w-4";
  switch (role?.toLowerCase()) {
    case "router":
      return <Router className={iconClass} />;
    case "switch":
    case "l2_switch":
    case "l3_switch":
      return <Wifi className={iconClass} />;
    case "firewall":
      return <Shield className={iconClass} />;
    case "server":
      return <Server className={iconClass} />;
    case "access_point":
    case "ap":
      return <MonitorSmartphone className={iconClass} />;
    default:
      return <Box className={iconClass} />;
  }
}

// Get shape based on device role
function getRoleShape(role: string | null): string {
  switch (role?.toLowerCase()) {
    case "router":
      return "diamond";
    case "switch":
    case "l2_switch":
    case "l3_switch":
      return "square";
    case "firewall":
      return "triangle";
    case "server":
      return "box";
    default:
      return "dot";
  }
}

export function TopologyMap({ nodes, edges, onRefresh, wsUrl }: TopologyMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const networkRef = useRef<Network | null>(null);
  const nodesDataSetRef = useRef<DataSet<any> | null>(null);
  const edgesDataSetRef = useRef<DataSet<any> | null>(null);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<TopologyNode | null>(null);
  const [hoveredEdge, setHoveredEdge] = useState<TopologyEdge | null>(null);
  const [isSearchOpen, setIsSearchOpen] = useState(false);

  // Initialize the network
  useEffect(() => {
    if (!containerRef.current) return;

    // Create DataSets for vis-network
    const visNodes = nodes.map((node) => ({
      id: node.id,
      label: node.label,
      color: {
        background: getNodeColor(node),
        border: node.type === "unknown" ? "#9ca3af" : getNodeColor(node),
        highlight: {
          background: getNodeColor(node),
          border: "#3b82f6",
        },
        hover: {
          background: getNodeColor(node),
          border: "#60a5fa",
        },
      },
      shape: getRoleShape(node.data.role),
      borderWidth: node.type === "unknown" ? 2 : 1,
      borderWidthSelected: 3,
      font: {
        color: "#f9fafb",
        size: 12,
        face: "Inter, system-ui, sans-serif",
      },
      title: `${node.label}${node.data.mgmt_ip ? `\n${node.data.mgmt_ip}` : ""}`,
      // Store original data for later use
      originalData: node,
    }));

    const visEdges = edges.map((edge) => ({
      id: edge.id,
      from: edge.source,
      to: edge.target,
      color: {
        color: "#6b7280",
        highlight: "#3b82f6",
        hover: "#9ca3af",
      },
      width: 1,
      smooth: {
        type: "curvedCW",
        roundness: 0.1,
      },
      title: `${edge.data.local_interface} ↔ ${edge.data.remote_interface}\n${edge.data.protocol.toUpperCase()}`,
      // Store original data for later use
      originalData: edge,
    }));

    nodesDataSetRef.current = new DataSet(visNodes);
    edgesDataSetRef.current = new DataSet(visEdges);

    const data: Data = {
      nodes: nodesDataSetRef.current,
      edges: edgesDataSetRef.current,
    };

    const options: Options = {
      layout: {
        improvedLayout: true,
        hierarchical: false,
      },
      physics: {
        enabled: true,
        solver: "forceAtlas2Based",
        forceAtlas2Based: {
          gravitationalConstant: -50,
          centralGravity: 0.01,
          springLength: 100,
          springConstant: 0.08,
          damping: 0.4,
          avoidOverlap: 0.5,
        },
        stabilization: {
          enabled: true,
          iterations: 200,
          updateInterval: 25,
        },
      },
      interaction: {
        hover: true,
        tooltipDelay: 200,
        hideEdgesOnDrag: false,
        navigationButtons: false,
        keyboard: {
          enabled: true,
          speed: { x: 10, y: 10, zoom: 0.03 },
          bindToWindow: false,
        },
        zoomView: true,
        dragView: true,
      },
      nodes: {
        size: 25,
        shadow: {
          enabled: true,
          color: "rgba(0,0,0,0.3)",
          size: 5,
          x: 2,
          y: 2,
        },
      },
      edges: {
        arrows: {
          to: { enabled: false },
        },
        shadow: {
          enabled: true,
          color: "rgba(0,0,0,0.2)",
          size: 3,
        },
      },
    };

    const network = new Network(containerRef.current, data, options);
    networkRef.current = network;

    // Event handlers
    network.on("click", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = nodes.find((n) => n.id === nodeId);
        setSelectedNode(node || null);
      } else {
        setSelectedNode(null);
      }
    });

    network.on("doubleClick", (params) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0];
        const node = nodes.find((n) => n.id === nodeId);
        if (node?.data.detail_url) {
          window.location.href = node.data.detail_url;
        }
      }
    });

    network.on("hoverEdge", (params) => {
      const edge = edges.find((e) => e.id === params.edge);
      setHoveredEdge(edge || null);
    });

    network.on("blurEdge", () => {
      setHoveredEdge(null);
    });

    // Cleanup
    return () => {
      network.destroy();
      networkRef.current = null;
    };
  }, [nodes, edges]);

  // Handle search
  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (!networkRef.current || !nodesDataSetRef.current) return;

    if (!query.trim()) {
      // Reset all nodes to original colors
      const updates = nodes.map((node) => ({
        id: node.id,
        color: {
          background: getNodeColor(node),
          border: node.type === "unknown" ? "#9ca3af" : getNodeColor(node),
        },
        font: { color: "#f9fafb" },
      }));
      nodesDataSetRef.current.update(updates);
      return;
    }

    const searchLower = query.toLowerCase();
    const updates = nodes.map((node) => {
      const matches =
        node.label.toLowerCase().includes(searchLower) ||
        node.data.mgmt_ip?.toLowerCase().includes(searchLower) ||
        node.data.vendor?.toLowerCase().includes(searchLower) ||
        node.data.site?.toLowerCase().includes(searchLower);

      return {
        id: node.id,
        color: {
          background: matches ? getNodeColor(node) : "#374151",
          border: matches ? (node.type === "unknown" ? "#9ca3af" : getNodeColor(node)) : "#374151",
        },
        font: { color: matches ? "#f9fafb" : "#6b7280" },
      };
    });
    nodesDataSetRef.current.update(updates);

    // Focus on first matching node
    const firstMatch = nodes.find(
      (node) =>
        node.label.toLowerCase().includes(searchLower) ||
        node.data.mgmt_ip?.toLowerCase().includes(searchLower)
    );
    if (firstMatch) {
      networkRef.current.focus(firstMatch.id, {
        scale: 1.5,
        animation: {
          duration: 500,
          easingFunction: "easeInOutQuad",
        },
      });
    }
  }, [nodes]);

  // Zoom controls
  const zoomIn = useCallback(() => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale();
      networkRef.current.moveTo({ scale: scale * 1.3, animation: true });
    }
  }, []);

  const zoomOut = useCallback(() => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale();
      networkRef.current.moveTo({ scale: scale / 1.3, animation: true });
    }
  }, []);

  const fitToScreen = useCallback(() => {
    if (networkRef.current) {
      networkRef.current.fit({
        animation: {
          duration: 500,
          easingFunction: "easeInOutQuad",
        },
      });
    }
  }, []);

  // WebSocket for real-time updates
  useEffect(() => {
    if (!wsUrl) return;

    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "device_status_changed" && nodesDataSetRef.current) {
          const deviceId = String(data.device_id);
          const node = nodes.find((n) => n.id === deviceId);
          if (node) {
            // Update node with new status
            const updatedNode = {
              ...node,
              data: {
                ...node.data,
                reachability_status: data.status,
              },
            };
            nodesDataSetRef.current.update({
              id: deviceId,
              color: {
                background: getNodeColor(updatedNode),
                border: getNodeColor(updatedNode),
              },
            });
          }
        }
      } catch (e) {
        console.error("Failed to parse WebSocket message:", e);
      }
    };

    return () => {
      ws.close();
    };
  }, [wsUrl, nodes]);

  return (
    <div className="relative h-full w-full">
      {/* Network Container */}
      <div
        ref={containerRef}
        className="h-full w-full bg-gray-950 rounded-lg border border-gray-800"
      />

      {/* Controls Toolbar */}
      <div className="absolute top-4 left-4 flex flex-col gap-2">
        {/* Search */}
        <Popover open={isSearchOpen} onOpenChange={setIsSearchOpen}>
          <PopoverTrigger asChild>
            <Button variant="secondary" size="icon" className="h-9 w-9 bg-gray-800/90 hover:bg-gray-700">
              <Search className="h-4 w-4" />
            </Button>
          </PopoverTrigger>
          <PopoverContent side="right" align="start" className="w-64">
            <div className="flex gap-2">
              <Input
                placeholder="Search devices..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                className="h-8"
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8"
                  onClick={() => handleSearch("")}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </PopoverContent>
        </Popover>

        {/* Zoom Controls */}
        <Button variant="secondary" size="icon" className="h-9 w-9 bg-gray-800/90 hover:bg-gray-700" onClick={zoomIn}>
          <ZoomIn className="h-4 w-4" />
        </Button>
        <Button variant="secondary" size="icon" className="h-9 w-9 bg-gray-800/90 hover:bg-gray-700" onClick={zoomOut}>
          <ZoomOut className="h-4 w-4" />
        </Button>
        <Button variant="secondary" size="icon" className="h-9 w-9 bg-gray-800/90 hover:bg-gray-700" onClick={fitToScreen}>
          <Maximize2 className="h-4 w-4" />
        </Button>

        {/* Refresh */}
        {onRefresh && (
          <Button variant="secondary" size="icon" className="h-9 w-9 bg-gray-800/90 hover:bg-gray-700" onClick={onRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        )}
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-gray-800/90 rounded-lg p-3 text-xs">
        <div className="font-medium mb-2 text-gray-300">Status Legend</div>
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: STATUS_COLORS.reachable }} />
            <span className="text-gray-400">Reachable</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: STATUS_COLORS.unreachable }} />
            <span className="text-gray-400">Unreachable</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: STATUS_COLORS.disabled }} />
            <span className="text-gray-400">Disabled</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: STATUS_COLORS.unknown }} />
            <span className="text-gray-400">Unknown</span>
          </div>
        </div>
      </div>

      {/* Selected Node Info Panel */}
      {selectedNode && (
        <Card className="absolute top-4 right-4 w-72 bg-gray-800/95 border-gray-700">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {getRoleIcon(selectedNode.data.role)}
                <CardTitle className="text-base">{selectedNode.label}</CardTitle>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setSelectedNode(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="text-sm">
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-gray-400">IP Address</span>
                <span className="font-mono">{selectedNode.data.mgmt_ip || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Vendor</span>
                <span>{selectedNode.data.vendor || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Platform</span>
                <span>{selectedNode.data.platform || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Site</span>
                <span>{selectedNode.data.site || "-"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Role</span>
                <span className="capitalize">{selectedNode.data.role || "-"}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-400">Status</span>
                <Badge
                  variant="secondary"
                  className="text-xs"
                  style={{
                    backgroundColor: getNodeColor(selectedNode),
                    color: "#fff",
                  }}
                >
                  {selectedNode.data.reachability_status || "Unknown"}
                </Badge>
              </div>
              {selectedNode.data.detail_url && (
                <Button
                  variant="secondary"
                  size="sm"
                  className="w-full mt-3"
                  onClick={() => window.location.href = selectedNode.data.detail_url!}
                >
                  View Device Details
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Hovered Edge Info */}
      {hoveredEdge && (
        <div className="absolute bottom-4 right-4 bg-gray-800/95 rounded-lg p-3 text-sm border border-gray-700">
          <div className="font-medium mb-1">Connection Details</div>
          <div className="text-gray-400 space-y-1">
            <div>Local: <span className="font-mono text-gray-200">{hoveredEdge.data.local_interface}</span></div>
            <div>Remote: <span className="font-mono text-gray-200">{hoveredEdge.data.remote_interface}</span></div>
            <div>Protocol: <Badge variant="secondary" className="text-xs">{hoveredEdge.data.protocol.toUpperCase()}</Badge></div>
          </div>
        </div>
      )}

      {/* Empty State */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center text-gray-400">
            <HelpCircle className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg font-medium">No topology data</p>
            <p className="text-sm">Run topology discovery to populate the map</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default TopologyMap;
