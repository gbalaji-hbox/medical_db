import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Download,
  ChevronRight,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Card, CardContent } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/loader";
import { Paginator } from "@/components/ui/paginator";
import { listJobs, downloadJob, runExisting } from "@/api/jobs";
import type { Job, Module } from "@/api/types";
import { MODULE_LABELS } from "@/api/types";
import { useAuth } from "@/store/auth";

const MODULES: (Module | "all")[] = ["all", "mca", "hct", "ssc", "cam", "cim", "xhi"];
const STATUSES = ["all", "pending", "running", "done", "error"];

function statusVariant(s: string): "success" | "secondary" | "destructive" | "outline" {
  if (s === "done") return "success";
  if (s === "running") return "secondary";
  if (s === "error" || s === "failed") return "destructive";
  return "outline";
}

function fmtTs(ts: number | null): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString();
}

function duration(j: Job): string {
  if (!j.started_at || !j.finished_at) return "—";
  const secs = Math.round(j.finished_at - j.started_at);
  if (secs < 60) return `${secs}s`;
  return `${Math.floor(secs / 60)}m ${secs % 60}s`;
}

function parseRecords(log: string): string {
  const m = log.match(/(\d[\d,]+)\s*records/i);
  return m ? m[1] : "—";
}

// ── Job detail drawer ─────────────────────────────────────────────────────────

function JobDrawer({
  job,
  onClose,
}: {
  job: Job | null;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const [rerunning, setRerunning] = useState(false);

  if (!job) return null;

  async function handleDownload() {
    if (!job) return;
    try {
      const blob = await downloadJob(job.module, job.job_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${job.module}_consolidated_${job.job_id.slice(0, 8)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch {
      toast({ variant: "destructive", title: "Download failed" });
    }
  }

  async function handleRerun() {
    if (!job) return;
    setRerunning(true);
    try {
      await runExisting(job.module);
      toast({ title: "Re-run started", description: `Module: ${job.module.toUpperCase()}` });
      onClose();
    } catch {
      toast({ variant: "destructive", title: "Re-run failed" });
    } finally {
      setRerunning(false);
    }
  }

  const steps = [
    { label: "Queued", ts: job.created_at },
    { label: "Started", ts: job.started_at },
    { label: "Finished", ts: job.finished_at },
  ];

  return (
    <Sheet open={!!job} onOpenChange={() => onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="mb-4">
          <SheetTitle>
            Job {job.job_id.slice(0, 12)}…
          </SheetTitle>
          <SheetDescription>
            {MODULE_LABELS[job.module]} · <Badge variant={statusVariant(job.status)}>{job.status}</Badge>
          </SheetDescription>
        </SheetHeader>

        {/* Timeline */}
        <div className="flex items-center gap-2 mb-6">
          {steps.map((s, i) => (
            <div key={s.label} className="flex items-center gap-2">
              <div className="text-xs text-center">
                <p className={`font-medium ${s.ts ? "text-foreground" : "text-muted-foreground"}`}>
                  {s.label}
                </p>
                <p className="text-muted-foreground">{fmtTs(s.ts)}</p>
              </div>
              {i < steps.length - 1 && (
                <ChevronRight size={14} className="text-muted-foreground shrink-0" />
              )}
            </div>
          ))}
        </div>

        {/* Meta */}
        <div className="grid grid-cols-2 gap-2 text-sm mb-6">
          <div className="rounded-md bg-muted px-3 py-2">
            <p className="text-xs text-muted-foreground">Submitted by</p>
            <p className="font-medium">{job.submitted_by ?? "—"}</p>
          </div>
          <div className="rounded-md bg-muted px-3 py-2">
            <p className="text-xs text-muted-foreground">Duration</p>
            <p className="font-medium">{duration(job)}</p>
          </div>
          <div className="rounded-md bg-muted px-3 py-2">
            <p className="text-xs text-muted-foreground">Return code</p>
            <p className="font-medium">{job.returncode ?? "—"}</p>
          </div>
          <div className="rounded-md bg-muted px-3 py-2">
            <p className="text-xs text-muted-foreground">Records</p>
            <p className="font-medium">{parseRecords(job.log)}</p>
          </div>
        </div>

        {/* Log */}
        <div className="mb-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Log Output
          </p>
          <pre className="rounded-md bg-muted p-3 text-xs overflow-auto max-h-64 whitespace-pre-wrap font-mono">
            {job.log || "(no log output)"}
          </pre>
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {job.status === "done" && (
            <Button className="gap-2" onClick={handleDownload}>
              <Download size={15} />
              Download Output
            </Button>
          )}
          <Button variant="outline" className="gap-2" disabled={rerunning} onClick={handleRerun}>
            {rerunning ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
            Re-run
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function JobsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [moduleFilter, setModuleFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const { data: jobs, isLoading, refetch } = useQuery({
    queryKey: ["jobs"],
    queryFn: () => listJobs(),
    refetchInterval: 10_000,
  });

  const filtered = (jobs ?? [])
    .filter((j) => {
      // Regular users see only their own jobs
      if (user?.role !== "admin" && j.submitted_by !== user?.username) return false;
      if (moduleFilter !== "all" && j.module !== moduleFilter) return false;
      if (statusFilter !== "all" && j.status !== statusFilter) return false;
      return true;
    })
    .sort((a, b) => b.created_at - a.created_at);
  const start = (page - 1) * pageSize;
  const visibleJobs = filtered.slice(start, start + pageSize);

  async function handleDownload(job: Job, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      const blob = await downloadJob(job.module, job.job_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${job.module}_consolidated_${job.job_id.slice(0, 8)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch {
      toast({ variant: "destructive", title: "Download failed" });
    }
  }

  if (isLoading) return <PageLoader text="Loading jobs…" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Job History</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {user?.role === "admin" ? "All pipeline runs" : "Your pipeline runs"}
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-2" onClick={() => refetch()}>
          <RefreshCw size={14} />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <Select
          value={moduleFilter}
          onValueChange={(value) => {
            setModuleFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Module" />
          </SelectTrigger>
          <SelectContent>
            {MODULES.map((m) => (
              <SelectItem key={m} value={m}>
                {m === "all" ? "All modules" : m.toUpperCase()}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value);
            setPage(1);
          }}
        >
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s === "all" ? "All statuses" : s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Module</TableHead>
                <TableHead>Status</TableHead>
                {user?.role === "admin" && <TableHead>Submitted by</TableHead>}
                <TableHead>Started</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>Records</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={user?.role === "admin" ? 7 : 6}
                    className="text-center text-muted-foreground py-12"
                  >
                    No jobs found.
                  </TableCell>
                </TableRow>
              ) : (
                visibleJobs.map((job) => (
                  <TableRow
                    key={job.job_id}
                    className="cursor-pointer"
                    onClick={() => setSelectedJob(job)}
                  >
                    <TableCell>
                      <Badge variant="outline">{MODULE_LABELS[job.module]}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={statusVariant(job.status)}>
                        {job.status === "running" && (
                          <Loader2 size={10} className="mr-1 animate-spin" />
                        )}
                        {job.status}
                      </Badge>
                    </TableCell>
                    {user?.role === "admin" && (
                      <TableCell className="text-sm">{job.submitted_by ?? "—"}</TableCell>
                    )}
                    <TableCell className="text-sm text-muted-foreground">
                      {fmtTs(job.started_at)}
                    </TableCell>
                    <TableCell className="text-sm">{duration(job)}</TableCell>
                    <TableCell className="text-sm">{parseRecords(job.log)}</TableCell>
                    <TableCell className="text-right">
                      {job.status === "done" && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 gap-1 text-xs"
                          onClick={(e) => handleDownload(job, e)}
                        >
                          <Download size={13} />
                          Download
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Paginator
        total={filtered.length}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPage(1);
        }}
        pageSizeOptions={[10, 25, 50, 100]}
      />

      <JobDrawer job={selectedJob} onClose={() => setSelectedJob(null)} />
    </div>
  );
}
