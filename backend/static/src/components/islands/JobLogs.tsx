import { useEffect, useMemo, useRef } from "react";

import { Badge } from "../ui/badge";

export type JobLog = {
  ts: string;
  level: string;
  host?: string;
  message: string;
};

type JobLogsProps = {
  jobId: number;
  status: string;
  logs: JobLog[];
};

export function JobLogs({ jobId, logs }: JobLogsProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const levelVariant = (level: string) => {
    const normalized = level.toLowerCase();
    if (normalized === "error") return "destructive" as const;
    if (normalized === "warning") return "outline" as const;
    if (normalized === "info") return "secondary" as const;
    return "outline" as const;
  };

  const orderedLogs = useMemo(() => logs.slice().sort((a, b) => a.ts.localeCompare(b.ts)), [logs]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [orderedLogs.length]);

  useEffect(() => {
    const handler = (event: Event) => {
      const detail = (event as CustomEvent).detail || {};
      if (detail.entity === "job" && Number(detail.id) === jobId) {
        const htmx = (window as any).htmx;
        if (htmx?.ajax) {
          htmx.ajax("GET", `/jobs/${jobId}/logs`, { target: "#job-logs", swap: "outerHTML" });
        }
      }
    };
    document.addEventListener("webnet:update", handler);
    return () => document.removeEventListener("webnet:update", handler);
  }, [jobId]);

  if (!orderedLogs.length) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
        </svg>
        <p className="text-sm">No logs available yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {orderedLogs.map((log, idx) => (
        <div key={`${log.ts}-${idx}`} className="flex items-start gap-3 text-sm p-2 rounded hover:bg-muted/50 transition-colors">
          <span className="text-muted-foreground font-mono text-xs whitespace-nowrap">{log.ts}</span>
          <Badge variant={levelVariant(log.level)} className="capitalize">
            {log.level}
          </Badge>
          {log.host ? (
            <Badge variant="outline">{log.host}</Badge>
          ) : null}
          <span className={`flex-1 ${log.level.toLowerCase() === "error" ? "text-destructive" : ""}`}>
            {log.message}
          </span>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}

export default JobLogs;
