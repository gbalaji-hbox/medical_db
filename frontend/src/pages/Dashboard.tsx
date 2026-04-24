import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Clock, Download, Loader2, Play } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { PageLoader } from "@/components/ui/loader";
import { listJobs, downloadJob } from "@/api/jobs";
import type { Job, Module } from "@/api/types";
import {
  MODULES,
  MODULE_LABELS,
  MODULE_CLINIC_NAMES,
  MODULE_DESCRIPTIONS,
} from "@/api/types";

// ── Helpers ──────────────────────────────────────────────────────────────────

const MODULE_COLORS: Record<string, string> = {
  mca: "#3b82f6",
  hct: "#10b981",
  ssc: "#f59e0b",
  cam: "#8b5cf6",
  cim: "#ef4444",
  xhi: "#ec4899",
};

function moduleColor(m: Module): string {
  return MODULE_COLORS[m] ?? "#6b7280";
}

function statusVariant(status: string) {
  if (status === "done") return "success";
  if (status === "running") return "secondary";
  if (status === "error" || status === "failed") return "destructive";
  return "outline";
}

function fmtTs(ts: number | null | undefined): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function duration(job: Job): string {
  if (!job.finished_at || !job.created_at) return "—";
  const secs = job.finished_at - job.created_at;
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function parseLogCounts(log: string) {
  const inMatch = log.match(/records?\s*(processed|input|in)[:\s]+(\d+)/i);
  const outMatch = log.match(/records?\s*(consolidated|output|out)[:\s]+(\d+)/i);
  return {
    recordsIn: inMatch ? parseInt(inMatch[2]) : null,
    recordsOut: outMatch ? parseInt(outMatch[2]) : null,
  };
}

function statusDotClass(status: string | undefined): string {
  if (status === "done") return "bg-emerald-500";
  if (status === "running") return "bg-blue-500 animate-pulse";
  if (status === "error" || status === "failed") return "bg-red-500";
  return "bg-gray-300 dark:bg-gray-600";
}

async function triggerDownload(module: Module, jobId: string) {
  const blob = await downloadJob(module, jobId);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${module}_consolidated_${jobId.slice(0, 8)}.xlsx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

// ── Job row ──────────────────────────────────────────────────────────────────

function JobRow({ job }: { job: Job }) {
  const [downloading, setDownloading] = useState(false);

  async function handleDownload() {
    setDownloading(true);
    try { await triggerDownload(job.module, job.job_id); }
    finally { setDownloading(false); }
  }

  return (
    <div className="flex items-center gap-3 py-2.5 border-b last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <code className="text-xs font-mono text-muted-foreground">
            {job.job_id.slice(0, 8)}…
          </code>
          <Badge variant={statusVariant(job.status)} className="text-xs">
            {job.status}
          </Badge>
        </div>
        <div className="flex items-center gap-3 mt-0.5 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Clock size={11} />
            {fmtTs(job.created_at)}
          </span>
          {job.finished_at && <span>{duration(job)}</span>}
        </div>
      </div>
      {job.status === "done" && (
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 shrink-0 h-7 text-xs"
          onClick={handleDownload}
          disabled={downloading}
        >
          {downloading ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <Download size={12} />
          )}
          Download
        </Button>
      )}
    </div>
  );
}

// ── Detail panel ─────────────────────────────────────────────────────────────

function ModuleDetail({
  module,
  jobs,
  onNavigate,
}: {
  module: Module;
  jobs: Job[];
  onNavigate: (path: string) => void;
}) {
  const [downloading, setDownloading] = useState(false);

  const sorted = [...jobs].sort((a, b) => b.created_at - a.created_at);
  const latest = sorted[0] ?? null;
  const recent = sorted.slice(0, 5);
  const counts = latest ? parseLogCounts(latest.log) : { recordsIn: null, recordsOut: null };

  async function handleDownload() {
    if (!latest || latest.status !== "done") return;
    setDownloading(true);
    try { await triggerDownload(module, latest.job_id); }
    finally { setDownloading(false); }
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-bold">
            {MODULE_LABELS[module]} — {MODULE_CLINIC_NAMES[module]}
          </h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {MODULE_DESCRIPTIONS[module]}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 shrink-0"
          onClick={() => onNavigate(`/upload?module=${module}`)}
        >
          <Play size={13} />
          Run Pipeline
        </Button>
      </div>

      {/* Last run card */}
      <Card>
        <CardHeader className="pb-2 pt-4">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Last Run
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4">
          {!latest ? (
            <div className="flex items-center gap-2 text-muted-foreground text-sm py-2">
              <AlertCircle size={15} />
              No jobs run yet for this module.
            </div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-4 flex-wrap">
                <div className="flex items-center gap-3 flex-wrap">
                  <Badge variant={statusVariant(latest.status)} className="text-sm px-2.5 py-0.5">
                    {latest.status}
                  </Badge>
                  <span className="text-sm text-muted-foreground flex items-center gap-1">
                    <Clock size={13} />
                    {fmtTs(latest.finished_at ?? latest.created_at)}
                  </span>
                  {latest.finished_at && (
                    <span className="text-sm text-muted-foreground">{duration(latest)}</span>
                  )}
                </div>
                {latest.status === "done" && (
                  <Button
                    size="sm"
                    className="gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white h-8"
                    onClick={handleDownload}
                    disabled={downloading}
                  >
                    {downloading ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <Download size={13} />
                    )}
                    Download Output
                  </Button>
                )}
              </div>

              <Separator />

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-2 text-sm">
                <div>
                  <p className="text-xs text-muted-foreground">Submitted by</p>
                  <p className="font-medium">{latest.submitted_by ?? "—"}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Records in</p>
                  <p className="font-medium">
                    {counts.recordsIn !== null ? counts.recordsIn.toLocaleString() : "—"}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Records out</p>
                  <p className="font-medium">
                    {counts.recordsOut !== null ? counts.recordsOut.toLocaleString() : "—"}
                  </p>
                </div>
              </div>

              {latest.log && (
                <p className="text-xs text-muted-foreground bg-muted/50 rounded px-2.5 py-1.5 truncate font-mono">
                  {latest.log.trim().split("\n").at(-1)}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent jobs */}
      <div>
        <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
          Recent Jobs
        </h3>
        <Card>
          <CardContent className="px-4 py-0">
            {recent.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">No jobs yet.</p>
            ) : (
              recent.map((job) => <JobRow key={job.job_id} job={job} />)
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function DashboardPage() {
  const navigate = useNavigate();
  const [selectedModule, setSelectedModule] = useState<Module>(MODULES[0]);

  const { data: allJobs, isLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs(),
    refetchInterval: 15_000,
  });

  if (isLoading) return <PageLoader text="Loading dashboard…" />;

  const jobsByModule = Object.fromEntries(
    MODULES.map((m) => [m, (allJobs ?? []).filter((j) => j.module === m)])
  ) as Record<Module, Job[]>;

  function latestJob(m: Module): Job | null {
    return [...(jobsByModule[m] ?? [])].sort((a, b) => b.created_at - a.created_at)[0] ?? null;
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Pipeline health across all clinic modules
        </p>
      </div>

      <div className="grid lg:grid-cols-[220px_1fr] gap-6 items-start">
        {/* Sidebar */}
        <Card className="lg:sticky lg:top-6">
          <CardHeader className="pb-1 pt-3 px-3">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Modules
            </CardTitle>
          </CardHeader>
          <CardContent className="px-2 pb-3 overflow-y-auto max-h-[70vh]">
            {MODULES.map((m) => {
              const latest = latestJob(m);
              const isSelected = m === selectedModule;
              return (
                <button
                  key={m}
                  onClick={() => setSelectedModule(m)}
                  className={`relative w-full flex items-center gap-2.5 px-3 py-2.5 rounded-md text-left transition-colors ${
                    isSelected
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-accent/50"
                  }`}
                >
                  {isSelected && (
                    <span
                      className="absolute left-0 top-1 bottom-1 w-0.75 rounded-r-lg"
                      style={{ background: moduleColor(m) }}
                    />
                  )}
                  <span
                    className={`h-2.5 w-2.5 rounded-full shrink-0 ${statusDotClass(latest?.status)}`}
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-semibold text-sm">{MODULE_LABELS[m]}</span>
                      {latest ? (
                        <Badge
                          variant={statusVariant(latest.status)}
                          className="text-[10px] px-1.5 py-0 h-4 leading-none"
                        >
                          {latest.status}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 leading-none">
                          idle
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground truncate mt-0.5">
                      {MODULE_CLINIC_NAMES[m]}
                    </p>
                  </div>
                </button>
              );
            })}
          </CardContent>
        </Card>

        {/* Detail panel */}
        <ModuleDetail
          module={selectedModule}
          jobs={jobsByModule[selectedModule] ?? []}
          onNavigate={navigate}
        />
      </div>
    </div>
  );
}
