import { useEffect, useMemo, useRef, useState } from "react";
import { Network, Options } from "vis-network/standalone";
import { DataSet } from "vis-data/standalone";
import {
  ArrowRight,
  Play,
  Save,
  Plus,
  Link2,
  Layers,
  Activity,
  Zap,
} from "lucide-react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Textarea } from "../ui/textarea";
import { Separator } from "../ui/separator";

type WorkflowNode = {
  id?: number;
  ref: string;
  name: string;
  category: "service" | "logic" | "data" | "notification";
  type: string;
  position_x: number;
  position_y: number;
  order_index?: number;
  config: Record<string, any>;
  ui_state?: Record<string, any> | null;
};

type WorkflowEdge = {
  source_ref: string;
  target_ref: string;
  condition?: string;
  label?: string;
  is_default?: boolean;
};

type Workflow = {
  id?: number;
  customer?: number;
  name: string;
  description?: string;
  is_active?: boolean;
  version?: number;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

type WorkflowRun = {
  id: number;
  status: string;
  steps?: Array<{ id: number; node_name: string; status: string; output?: unknown }>;
};

type PaletteItem = {
  category: WorkflowNode["category"];
  type: string;
  label: string;
  description?: string;
  config?: Record<string, any>;
};

type WorkflowBuilderProps = {
  apiBase: string;
  runEndpoint: string;
  availableWorkflows: Array<{ id: number; name: string; version?: number; customer_id?: number }>;
  workflow?: Workflow;
  nodePalette: PaletteItem[];
  csrfToken?: string;
};

type VisNode = {
  id: string;
  label: string;
  color: { background: string; border: string };
  shape: string;
  x?: number;
  y?: number;
  title?: string;
};

const CATEGORY_COLORS: Record<WorkflowNode["category"], string> = {
  service: "#2563eb",
  logic: "#f97316",
  data: "#22c55e",
  notification: "#a855f7",
};

function categoryShape(category: WorkflowNode["category"]): string {
  switch (category) {
    case "service":
      return "box";
    case "logic":
      return "diamond";
    case "data":
      return "ellipse";
    case "notification":
      return "hexagon";
    default:
      return "dot";
  }
}

function hydrateRef(ref?: string): string {
  if (ref) return ref;
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return (crypto as Crypto).randomUUID();
  }
  return Math.random().toString(36).slice(2);
}

function sanitizeJson(value: string): Record<string, unknown> | undefined {
  if (!value.trim()) return {};
  try {
    return JSON.parse(value);
  } catch (err) {
    console.warn("Failed to parse JSON", err);
    return undefined;
  }
}

export default function WorkflowBuilder({
  apiBase,
  runEndpoint,
  availableWorkflows,
  workflow,
  nodePalette,
  csrfToken,
}: WorkflowBuilderProps) {
  const [meta, setMeta] = useState<Workflow>({
    id: workflow?.id,
    name: workflow?.name || "New Workflow",
    description: workflow?.description || "",
    customer: workflow?.customer || availableWorkflows[0]?.customer_id,
    is_active: workflow?.is_active ?? true,
    version: workflow?.version,
    nodes: workflow?.nodes || [],
    edges: workflow?.edges || [],
  });
  const [nodes, setNodes] = useState<WorkflowNode[]>(workflow?.nodes || []);
  const [edges, setEdges] = useState<WorkflowEdge[]>(workflow?.edges || []);
  const [selectedRef, setSelectedRef] = useState<string | null>(
    workflow?.nodes?.[0]?.ref || null
  );
  const [connectFrom, setConnectFrom] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("");
  const [runResult, setRunResult] = useState<WorkflowRun | null>(null);
  const [inputJson, setInputJson] = useState<string>("{}");

  const containerRef = useRef<HTMLDivElement | null>(null);
  const networkRef = useRef<Network | null>(null);
  const nodesData = useRef<DataSet<VisNode> | null>(null);
  const edgesData = useRef<DataSet<any> | null>(null);

  const options: Options = useMemo(
    () => ({
      autoResize: true,
      interaction: { hover: true, dragNodes: true },
      physics: { enabled: true, stabilization: true },
      layout: { improvedLayout: true, hierarchical: false },
      edges: { arrows: "to", smooth: { type: "dynamic" } },
    }),
    []
  );

  useEffect(() => {
    if (!containerRef.current) return;
    nodesData.current = new DataSet();
    edgesData.current = new DataSet();
    networkRef.current = new Network(
      containerRef.current,
      { nodes: nodesData.current, edges: edgesData.current },
      options
    );
    networkRef.current.on("selectNode", (event) => {
      const ref = event.nodes?.[0];
      if (ref) setSelectedRef(String(ref));
    });
  }, [options]);

  useEffect(() => {
    if (!nodesData.current) return;
    const visNodes: VisNode[] = nodes.map((node) => ({
      id: node.ref,
      label: node.name,
      title: `${node.category}:${node.type}`,
      x: node.position_x,
      y: node.position_y,
      shape: categoryShape(node.category),
      color: {
        background: CATEGORY_COLORS[node.category],
        border: "#0f172a",
      },
    }));
    nodesData.current.clear();
    nodesData.current.add(visNodes);
  }, [nodes]);

  useEffect(() => {
    if (!edgesData.current) return;
    const visEdges = edges.map((edge, idx) => ({
      id: `${edge.source_ref}-${edge.target_ref}-${idx}`,
      from: edge.source_ref,
      to: edge.target_ref,
      label: edge.label || "",
      dashes: edge.condition ? true : false,
      color: { color: edge.condition ? "#f97316" : "#6b7280" },
      arrows: "to",
    }));
    edgesData.current.clear();
    edgesData.current.add(visEdges);
  }, [edges]);

  const selectedNode = nodes.find((n) => n.ref === selectedRef);

  function addNodeFromTemplate(item: PaletteItem) {
    const ref = hydrateRef();
    const newNode: WorkflowNode = {
      ref,
      name: item.label,
      category: item.category,
      type: item.type,
      position_x: Math.random() * 200,
      position_y: Math.random() * 200,
      config: { ...(item.config || {}) },
      ui_state: {},
    };
    setNodes((prev) => [...prev, newNode]);
    setSelectedRef(ref);
    setStatus(`Added ${item.label}`);
  }

  function updateNode(ref: string, updates: Partial<WorkflowNode>) {
    setNodes((prev) =>
      prev.map((node) => (node.ref === ref ? { ...node, ...updates } : node))
    );
  }

  function connectNodes(sourceRef: string, targetRef: string) {
    if (sourceRef === targetRef) {
      setStatus("Cannot connect a node to itself");
      return;
    }
    const exists = edges.some(
      (edge) => edge.source_ref === sourceRef && edge.target_ref === targetRef
    );
    if (exists) {
      setStatus("Edge already exists");
      return;
    }
    setEdges((prev) => [...prev, { source_ref: sourceRef, target_ref: targetRef }]);
    setStatus("Edge added");
  }

  async function saveWorkflow() {
    const payload: Workflow = { ...meta, nodes, edges };
    const method = payload.id ? "PUT" : "POST";
    const url = payload.id ? `${apiBase}${payload.id}/` : apiBase;
    try {
      const resp = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || "Failed to save workflow");
      }
      const data: Workflow = await resp.json();
      setMeta((prev) => ({ ...prev, id: data.id, version: data.version }));
      setNodes(data.nodes || []);
      setEdges(data.edges || []);
      setStatus("Workflow saved");
    } catch (err) {
      console.error(err);
      setStatus(err instanceof Error ? err.message : "Failed to save workflow");
    }
  }

  async function runWorkflow() {
    if (!meta.id) {
      setStatus("Save the workflow before running");
      return;
    }
    const inputs = sanitizeJson(inputJson) || {};
    try {
      const resp = await fetch(runEndpoint.replace("{id}", String(meta.id)), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
        },
        body: JSON.stringify({ inputs }),
      });
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || "Run failed");
      }
      const data: WorkflowRun = await resp.json();
      setRunResult(data);
      setStatus(`Run ${data.id} status: ${data.status}`);
    } catch (err) {
      console.error(err);
      setStatus(err instanceof Error ? err.message : "Run failed");
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-4 p-4">
      <div className="space-y-4 lg:col-span-1">
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-4 w-4" />
              Workflow
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1">
              <Label className="text-xs uppercase text-muted-foreground">Name</Label>
              <Input
                value={meta.name}
                onChange={(e) => setMeta({ ...meta, name: e.target.value })}
                placeholder="Incident response"
              />
            </div>
            <div className="space-y-1">
              <Label className="text-xs uppercase text-muted-foreground">Description</Label>
              <Textarea
                value={meta.description}
                onChange={(e) => setMeta({ ...meta, description: e.target.value })}
                rows={3}
              />
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Badge variant="secondary">v{meta.version || 1}</Badge>
              <span>{nodes.length} nodes · {edges.length} edges</span>
            </div>
            <div className="flex gap-2">
              <Button className="flex-1" onClick={saveWorkflow}>
                <Save className="h-4 w-4 mr-2" />
                Save
              </Button>
              <Button variant="outline" onClick={runWorkflow}>
                <Play className="h-4 w-4 mr-2" />
                Run
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Nodes
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {nodePalette.map((item) => (
              <button
                key={`${item.category}-${item.type}`}
                onClick={() => addNodeFromTemplate(item)}
                className="w-full rounded-md border px-3 py-2 text-left hover:bg-muted"
              >
                <div className="flex items-center justify-between">
                  <div className="font-medium">{item.label}</div>
                  <Badge className="capitalize" variant="outline">
                    {item.category}
                  </Badge>
                </div>
                {item.description && (
                  <p className="text-xs text-muted-foreground">{item.description}</p>
                )}
              </button>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Inputs
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Label className="text-xs uppercase text-muted-foreground">Run inputs (JSON)</Label>
            <Textarea
              rows={4}
              value={inputJson}
              onChange={(e) => setInputJson(e.target.value)}
              className="font-mono text-xs"
            />
            {runResult && (
              <div className="rounded-md border bg-muted p-2 text-xs">
                Run #{runResult.id} · {runResult.status}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-4 lg:col-span-3">
        <Card className="h-[520px]">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Canvas
            </CardTitle>
            <div className="flex items-center gap-2">
              <Button
                variant={connectFrom ? "default" : "outline"}
                size="sm"
                onClick={() => setConnectFrom(selectedRef)}
                disabled={!selectedRef}
              >
                <Link2 className="h-4 w-4 mr-1" />
                {connectFrom ? "Select target" : "Start link"}
              </Button>
              {connectFrom && selectedRef && selectedRef !== connectFrom && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    connectNodes(connectFrom, selectedRef);
                    setConnectFrom(null);
                  }}
                >
                  <ArrowRight className="h-4 w-4 mr-1" />
                  Connect
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="h-[460px]">
            <div ref={containerRef} className="h-full w-full rounded-md border bg-muted/50" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers className="h-4 w-4" />
              Node Inspector
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!selectedNode && <p className="text-muted-foreground text-sm">Select a node to edit.</p>}
            {selectedNode && (
              <div className="grid gap-3 md:grid-cols-2">
                <div className="space-y-1">
                  <Label>Name</Label>
                  <Input
                    value={selectedNode.name}
                    onChange={(e) => updateNode(selectedNode.ref, { name: e.target.value })}
                  />
                </div>
                <div className="space-y-1">
                  <Label>Type</Label>
                  <Input
                    value={selectedNode.type}
                    onChange={(e) => updateNode(selectedNode.ref, { type: e.target.value })}
                  />
                </div>
                <div className="space-y-1 md:col-span-2">
                  <Label>Config (JSON)</Label>
                  <Textarea
                    className="font-mono text-xs"
                    rows={4}
                    value={JSON.stringify(selectedNode.config || {}, null, 2)}
                    onChange={(e) => {
                      const parsed = sanitizeJson(e.target.value);
                      if (parsed) {
                        updateNode(selectedNode.ref, { config: parsed });
                      }
                    }}
                  />
                </div>
                <div className="md:col-span-2 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEdges((prev) =>
                        prev.filter(
                          (edge) =>
                            edge.source_ref !== selectedNode.ref &&
                            edge.target_ref !== selectedNode.ref
                        )
                      );
                      setNodes((prev) => prev.filter((node) => node.ref !== selectedNode.ref));
                      setSelectedRef(null);
                    }}
                  >
                    Remove Node
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
        {status && (
          <div className="rounded-md border bg-muted px-3 py-2 text-sm flex items-center gap-2">
            <Activity className="h-4 w-4" />
            <span>{status}</span>
          </div>
        )}
      </div>
    </div>
  );
}
