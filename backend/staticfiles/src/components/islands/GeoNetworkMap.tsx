import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import L, { LatLngExpression, Map } from "leaflet";
import "leaflet/dist/leaflet.css";
import { RefreshCw, Search, Crosshair, MapPin, Link2, Layers } from "lucide-react";

import { Badge } from "../ui/badge";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Input } from "../ui/input";
import { ScrollArea } from "../ui/scroll-area";
import { Separator } from "../ui/separator";

type GeoMapProps = {
  dataUrl: string;
  initialCenter?: [number, number];
  initialZoom?: number;
};

type DeviceNode = {
  id: number;
  hostname: string;
  mgmt_ip: string | null;
  vendor: string | null;
  platform: string | null;
  role: string | null;
  status: string;
  reachability_status: string | null;
  detail_url: string | null;
};

type SiteNode = {
  id: string;
  name: string;
  customer_id: number;
  latitude: number;
  longitude: number;
  address?: string | null;
  device_count: number;
  reachable_devices: number;
  unreachable_devices: number;
  disabled_devices: number;
  unknown_devices: number;
  status: string;
  devices: DeviceNode[];
};

type LinkEdge = {
  id: string;
  source: string;
  target: string;
  source_name: string;
  target_name: string;
  count: number;
  status: string;
};

type MapResponse = {
  sites: SiteNode[];
  links: LinkEdge[];
};

const STATUS_COLORS: Record<string, string> = {
  healthy: "#10b981",
  degraded: "#f59e0b",
  down: "#ef4444",
  maintenance: "#94a3b8",
  unknown: "#94a3b8",
};

const LINK_COLORS: Record<string, string> = {
  up: "#10b981",
  degraded: "#f59e0b",
  down: "#ef4444",
  unknown: "#94a3b8",
};

const DEFAULT_CENTER: [number, number] = [20, 0];

function statusColor(status: string): string {
  return STATUS_COLORS[status] || STATUS_COLORS.unknown;
}

function linkColor(status: string): string {
  return LINK_COLORS[status] || LINK_COLORS.unknown;
}

export function GeoNetworkMap({
  dataUrl,
  initialCenter = DEFAULT_CENTER,
  initialZoom = 2,
}: GeoMapProps) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const markersRef = useRef<L.LayerGroup | null>(null);
  const linksRef = useRef<L.LayerGroup | null>(null);

  const [sites, setSites] = useState<SiteNode[]>([]);
  const [links, setLinks] = useState<LinkEdge[]>([]);
  const [selectedSite, setSelectedSite] = useState<SiteNode | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    const map = L.map(mapContainerRef.current, { zoomControl: false }).setView(
      initialCenter as LatLngExpression,
      initialZoom
    );
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>',
      maxZoom: 19,
    }).addTo(map);
    L.control.zoom({ position: "bottomright" }).addTo(map);
    markersRef.current = L.layerGroup().addTo(map);
    linksRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
  }, [initialCenter, initialZoom]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await fetch(dataUrl, { headers: { Accept: "application/json" } });
      if (!resp.ok) {
        throw new Error(`Request failed with ${resp.status}`);
      }
      const payload = (await resp.json()) as MapResponse;
      setSites(payload.sites || []);
      setLinks(payload.links || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load map data");
    } finally {
      setLoading(false);
    }
  }, [dataUrl]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const filteredSites = useMemo(() => {
    const term = search.trim().toLowerCase();
    return sites.filter((site) => {
      const matchesStatus = statusFilter === "all" || site.status === statusFilter;
      if (!matchesStatus) return false;
      if (!term) return true;
      if (site.name.toLowerCase().includes(term)) return true;
      return site.devices.some((d) => d.hostname.toLowerCase().includes(term));
    });
  }, [sites, search, statusFilter]);

  const siteLookup = useMemo(() => {
    const lookup: Record<string, SiteNode> = {};
    filteredSites.forEach((site) => {
      lookup[site.id] = site;
    });
    return lookup;
  }, [filteredSites]);

  const filteredLinks = useMemo(
    () => links.filter((link) => siteLookup[link.source] && siteLookup[link.target]),
    [links, siteLookup]
  );

  useEffect(() => {
    const map = mapRef.current;
    const markersLayer = markersRef.current;
    const linksLayer = linksRef.current;
    if (!map || !markersLayer || !linksLayer) return;

    markersLayer.clearLayers();
    linksLayer.clearLayers();

    filteredLinks.forEach((edge) => {
      const source = siteLookup[edge.source];
      const target = siteLookup[edge.target];
      if (!source || !target) return;
      const line = L.polyline(
        [
          [source.latitude, source.longitude],
          [target.latitude, target.longitude],
        ],
        {
          color: linkColor(edge.status),
          weight: 3,
          opacity: 0.7,
          dashArray: edge.status === "degraded" ? "6 6" : undefined,
        }
      );
      line.bindTooltip(
        `${source.name} ⇄ ${target.name} • ${edge.count} link${edge.count > 1 ? "s" : ""}`,
        { direction: "top" }
      );
      line.addTo(linksLayer);
    });

    filteredSites.forEach((site) => {
      const marker = L.circleMarker([site.latitude, site.longitude], {
        radius: Math.min(22, 10 + Math.log(site.device_count + 1) * 5),
        color: "#0f172a",
        weight: 1.5,
        fillColor: statusColor(site.status),
        fillOpacity: 0.9,
        className: "geo-site-marker",
      });
      marker.on("click", () => {
        setSelectedSite(site);
        map.flyTo([site.latitude, site.longitude], Math.max(map.getZoom(), 6), {
          duration: 0.35,
        });
      });
      marker.bindTooltip(`${site.name} • ${site.device_count} device(s)`, {
        direction: "top",
      });
      marker.addTo(markersLayer);
    });

    if (filteredSites.length) {
      const bounds = L.latLngBounds(
        filteredSites.map((s) => [s.latitude, s.longitude] as [number, number])
      );
      map.fitBounds(bounds.pad(0.2));
    }
  }, [filteredSites, filteredLinks, siteLookup]);

  const handleResetView = () => {
    if (!mapRef.current) return;
    if (filteredSites.length) {
      const bounds = L.latLngBounds(
        filteredSites.map((s) => [s.latitude, s.longitude] as [number, number])
      );
      mapRef.current.fitBounds(bounds.pad(0.2));
    } else {
      mapRef.current.setView(initialCenter, initialZoom);
    }
  };

  return (
    <div className="relative flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-wrap items-center gap-2">
          {["all", "healthy", "degraded", "down", "maintenance", "unknown"].map((status) => (
            <Button
              key={status}
              size="sm"
              variant={statusFilter === status ? "default" : "outline"}
              className="capitalize"
              onClick={() => setStatusFilter(status)}
            >
              <span
                className="mr-2 inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: status === "all" ? "#6366f1" : statusColor(status) }}
              />
              {status === "all" ? "All" : status}
            </Button>
          ))}
        </div>
        <div className="ml-auto flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search site or device"
              className="pl-8 w-52"
            />
          </div>
          <Button variant="outline" size="icon" onClick={handleResetView} title="Fit to sites">
            <Crosshair className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="icon" onClick={fetchData} title="Refresh data">
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <div className="relative flex-1 overflow-hidden rounded-lg border bg-muted/20">
        <div ref={mapContainerRef} className="absolute inset-0" />

        {loading && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/70 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-2 text-muted-foreground">
              <RefreshCw className="h-5 w-5 animate-spin" />
              <p className="text-sm">Loading geographic map…</p>
            </div>
          </div>
        )}

        {error && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80">
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          </div>
        )}

        {selectedSite && (
          <Card className="absolute right-3 top-3 z-20 w-80 max-h-[80vh] overflow-hidden shadow-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-muted-foreground" />
                <span className="truncate">{selectedSite.name}</span>
              </CardTitle>
              <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
                <Badge
                  variant="outline"
                  className="gap-1"
                  style={{ borderColor: statusColor(selectedSite.status) }}
                >
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: statusColor(selectedSite.status) }}
                  />
                  {selectedSite.status}
                </Badge>
                <span>{selectedSite.device_count} devices</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {selectedSite.address && (
                <p className="text-sm text-muted-foreground">{selectedSite.address}</p>
              )}
              <div className="grid grid-cols-2 gap-2 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <Badge className="bg-emerald-500 hover:bg-emerald-500">up</Badge>
                  {selectedSite.reachable_devices}
                </div>
                <div className="flex items-center gap-1">
                  <Badge className="bg-red-500 hover:bg-red-500">down</Badge>
                  {selectedSite.unreachable_devices}
                </div>
                <div className="flex items-center gap-1">
                  <Badge className="bg-amber-500 hover:bg-amber-500">unknown</Badge>
                  {selectedSite.unknown_devices}
                </div>
                <div className="flex items-center gap-1">
                  <Badge className="bg-slate-400 hover:bg-slate-400">disabled</Badge>
                  {selectedSite.disabled_devices}
                </div>
              </div>
              <Separator />
              <div className="flex items-center gap-2 text-xs font-medium uppercase text-muted-foreground">
                <Layers className="h-3.5 w-3.5" />
                Devices at this site
              </div>
              <ScrollArea className="h-48">
                <div className="space-y-2 pr-1">
                  {selectedSite.devices.map((device) => (
                    <a
                      key={device.id}
                      href={device.detail_url || "#"}
                      className="block rounded-md border bg-background px-3 py-2 shadow-sm transition hover:border-primary"
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium">{device.hostname}</span>
                        <Badge
                          variant="outline"
                          className="gap-1"
                          style={{ borderColor: statusColor(device.status) }}
                        >
                          <span
                            className="inline-block h-2 w-2 rounded-full"
                            style={{ backgroundColor: statusColor(device.status) }}
                          />
                          {device.status}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {device.mgmt_ip || "No IP"} • {device.role || "unspecified"}
                      </div>
                    </a>
                  ))}
                  {!selectedSite.devices.length && (
                    <p className="text-xs text-muted-foreground">No devices for this site.</p>
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        )}
      </div>

      {!filteredSites.length && !loading && (
        <div className="rounded-md border border-dashed px-4 py-3 text-sm text-muted-foreground">
          No sites with coordinates yet. Add latitude/longitude to devices or create site data to
          see them on the map.
        </div>
      )}

      <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
        <div className="inline-flex items-center gap-1 rounded-full border bg-background px-2 py-1">
          <MapPin className="h-3 w-3" />
          Site markers are sized by device count and colored by health.
        </div>
        <div className="inline-flex items-center gap-1 rounded-full border bg-background px-2 py-1">
          <Link2 className="h-3 w-3" />
          Lines show discovered site-to-site links and their status.
        </div>
      </div>
    </div>
  );
}

export default GeoNetworkMap;
