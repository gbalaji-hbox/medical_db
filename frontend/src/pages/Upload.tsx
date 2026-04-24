import { useState, useRef, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Upload as UploadIcon,
  X,
  Download,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Play,
  RefreshCw,
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { processFiles, runExisting, getJob, downloadJob, downloadSample } from "@/api/jobs";
import type { Module } from "@/api/types";
import { MODULES, MODULE_LABELS, MODULE_DESCRIPTIONS } from "@/api/types";
import { consolidatedDownloadFilename } from "@/lib/downloadFilename";
import { MODULE_FILE_SLOTS, type FileSlot } from "@/config/moduleFiles";

const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB

interface SlotState {
  file: File | null;
  error: string | null;
  uploading: boolean;
}

// ── File Slot Row ─────────────────────────────────────────────────────────────

function FileSlotRow({
  slot,
  state,
  module,
  onFile,
  onClear,
}: {
  slot: FileSlot;
  state: SlotState;
  module: Module;
  onFile: (field: string, file: File) => void;
  onClear: (field: string) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) onFile(slot.field, f);
    },
    [onFile, slot.field]
  );

  const handleSampleDownload = async () => {
    if (!slot.sampleFile) return;
    try {
      const blob = await downloadSample(module, slot.sampleFile);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = slot.sampleFile;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch {
      alert("Sample file not available yet.");
    }
  };

  const filled = !!state.file;

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={`rounded-lg border-2 transition-colors p-3 ${
        dragging
          ? "border-primary bg-primary/5"
          : filled
          ? "border-emerald-400 bg-emerald-50/50"
          : state.error
          ? "border-destructive/50 bg-destructive/5"
          : "border-dashed border-border hover:border-primary/50"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* Status icon */}
        <div className="mt-0.5 shrink-0">
          {filled ? (
            <CheckCircle2 size={18} className="text-emerald-500" />
          ) : state.error ? (
            <AlertCircle size={18} className="text-destructive" />
          ) : (
            <UploadIcon size={18} className="text-muted-foreground" />
          )}
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-sm">{slot.label}</span>
            <Badge variant={slot.required ? "default" : "outline"} className="text-xs py-0">
              {slot.required ? "Required" : "Optional"}
            </Badge>
          </div>
          {slot.description && (
            <p className="text-xs text-muted-foreground mt-0.5">{slot.description}</p>
          )}

          {filled && state.file ? (
            <p className="text-xs text-emerald-700 mt-1 font-medium truncate">
              {state.file.name} · {(state.file.size / 1024 / 1024).toFixed(1)} MB
            </p>
          ) : state.error ? (
            <p className="text-xs text-destructive mt-1">{state.error}</p>
          ) : (
            <p className="text-xs text-muted-foreground mt-1">
              Drag & drop or{" "}
              <button
                type="button"
                className="text-primary underline underline-offset-2 hover:no-underline"
                onClick={() => inputRef.current?.click()}
              >
                browse
              </button>
              {" "}· {slot.accept} · max 50 MB
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          {slot.sampleFile && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={handleSampleDownload}
              title="Download sample file"
            >
              <Download size={13} />
              Sample
            </Button>
          )}
          {filled ? (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-destructive"
              onClick={() => onClear(slot.field)}
            >
              <X size={14} />
            </Button>
          ) : (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => inputRef.current?.click()}
            >
              <UploadIcon size={14} />
            </Button>
          )}
        </div>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={slot.accept}
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) onFile(slot.field, f);
          e.target.value = "";
        }}
      />
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function UploadPage() {
  const [searchParams] = useSearchParams();
  const { toast } = useToast();

  const defaultModule = (searchParams.get("module") as Module) ?? "mca";
  const [module, setModule] = useState<Module>(defaultModule);

  // When URL param changes, update module
  useEffect(() => {
    const m = searchParams.get("module") as Module | null;
    if (m && MODULES.includes(m)) setModule(m);
  }, [searchParams]);

  const slots = MODULE_FILE_SLOTS[module];

  const [slotStates, setSlotStates] = useState<Record<string, SlotState>>({});
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [completedJob, setCompletedJob] = useState<{
    id: string;
    module: Module;
    finishedAt: number | null;
    createdAt: number;
  } | null>(null);
  const [downloading, setDownloading] = useState(false);
  const moduleRef = useRef<Module>(module);

  // Keep moduleRef in sync so pollJob closure always reads current module
  useEffect(() => {
    moduleRef.current = module;
  }, [module]);

  // Reset slots when module changes
  useEffect(() => {
    setSlotStates({});
    setJobId(null);
    setCompletedJob(null);
  }, [module]);

  function handleFile(field: string, file: File) {
    if (file.size > MAX_FILE_SIZE) {
      setSlotStates((prev) => ({
        ...prev,
        [field]: { file: null, error: "File exceeds 50 MB limit.", uploading: false },
      }));
      return;
    }
    setSlotStates((prev) => ({
      ...prev,
      [field]: { file, error: null, uploading: false },
    }));
  }

  function handleClear(field: string) {
    setSlotStates((prev) => ({
      ...prev,
      [field]: { file: null, error: null, uploading: false },
    }));
  }

  const requiredSlots = slots.filter((s) => s.required);
  const allRequiredFilled = requiredSlots.every(
    (s) => !!slotStates[s.field]?.file
  );

  async function handleRun() {
    setRunning(true);
    setProgress(10);
    try {
      const files: Record<string, File> = {};
      for (const slot of slots) {
        const f = slotStates[slot.field]?.file;
        if (f) files[slot.field] = f;
      }
      const result = await processFiles(module, files);
      setJobId(result.job_id);
      setProgress(30);
      toast({ title: "Pipeline started", description: `Job ID: ${result.job_id}` });
      pollJob(result.job_id);
    } catch {
      toast({ variant: "destructive", title: "Failed to start pipeline", description: "Check your files and try again." });
      setRunning(false);
      setProgress(0);
    }
  }

  async function handleRunExisting() {
    setRunning(true);
    setProgress(10);
    try {
      const result = await runExisting(module);
      setJobId(result.job_id);
      setProgress(30);
      toast({ title: "Pipeline started with existing files", description: `Job ID: ${result.job_id}` });
      pollJob(result.job_id);
    } catch {
      toast({ variant: "destructive", title: "Failed to start pipeline" });
      setRunning(false);
      setProgress(0);
    }
  }

  function pollJob(id: string) {
    const interval = setInterval(async () => {
      try {
        const job = await getJob(moduleRef.current, id);
        if (job.status === "done") {
          clearInterval(interval);
          setProgress(100);
          setRunning(false);
          setCompletedJob({
            id,
            module: moduleRef.current,
            finishedAt: job.finished_at,
            createdAt: job.created_at,
          });
          toast({ title: "Pipeline complete!", description: "Download your output below." });
        } else if (job.status === "error" || job.status === "failed") {
          clearInterval(interval);
          setProgress(0);
          setRunning(false);
          toast({
            variant: "destructive",
            title: "Pipeline failed",
            description: job.log?.slice(-200) ?? "Check job logs.",
          });
        } else {
          setProgress((p) => Math.min(p + 5, 85));
        }
      } catch {
        clearInterval(interval);
        setRunning(false);
      }
    }, 3000);
  }

  async function handleDownload() {
    if (!completedJob) return;
    setDownloading(true);
    try {
      const blob = await downloadJob(completedJob.module, completedJob.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = consolidatedDownloadFilename(
        completedJob.module,
        completedJob.finishedAt ?? completedJob.createdAt
      );
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch {
      toast({ variant: "destructive", title: "Download failed" });
    } finally {
      setDownloading(false);
    }
  }

  const filledCount = slots.filter((s) => !!slotStates[s.field]?.file).length;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Upload Files</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Select the clinic module, upload raw export files, then run the pipeline.
        </p>
      </div>

      {/* Module selector */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Select Clinic Module</CardTitle>
          <CardDescription>
            Each module corresponds to a different clinic's EHR system with its own required files.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <Select value={module} onValueChange={(v) => setModule(v as Module)}>
            <SelectTrigger className="w-full sm:w-72">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {MODULES.map((m) => (
                <SelectItem key={m} value={m}>
                  <span className="font-medium">{MODULE_LABELS[m]}</span>
                  <span className="ml-2 text-xs text-muted-foreground">
                    {MODULE_DESCRIPTIONS[m].split("(")[1]?.replace(")", "") ?? ""}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {MODULE_DESCRIPTIONS[module]}
          </p>
        </CardContent>
      </Card>

      <div className="grid lg:grid-cols-[1fr_280px] gap-6">
        {/* Left — file slots */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">File Upload Slots</CardTitle>
            <CardDescription>
              {filledCount} / {slots.length} files provided
              {requiredSlots.length > 0 && ` · ${requiredSlots.length} required`}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {slots.map((slot) => (
              <FileSlotRow
                key={slot.field}
                slot={slot}
                state={slotStates[slot.field] ?? { file: null, error: null, uploading: false }}
                module={module}
                onFile={handleFile}
                onClear={handleClear}
              />
            ))}
          </CardContent>
        </Card>

        {/* Right — run controls */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Run Controls</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Slot summary */}
              <div className="space-y-1.5 text-sm">
                {slots.map((slot) => {
                  const filled = !!slotStates[slot.field]?.file;
                  return (
                    <div key={slot.field} className="flex items-center gap-2">
                      {filled ? (
                        <CheckCircle2 size={14} className="text-emerald-500 shrink-0" />
                      ) : slot.required ? (
                        <AlertCircle size={14} className="text-amber-500 shrink-0" />
                      ) : (
                        <div className="h-3.5 w-3.5 rounded-full border border-border shrink-0" />
                      )}
                      <span className={`truncate ${filled ? "text-foreground" : "text-muted-foreground"}`}>
                        {slot.label}
                      </span>
                      {!slot.required && (
                        <span className="text-xs text-muted-foreground shrink-0">opt</span>
                      )}
                    </div>
                  );
                })}
              </div>

              <Separator />

              {running && (
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{jobId ? `Job ${jobId.slice(0, 8)}…` : "Starting…"}</span>
                    <span>{progress}%</span>
                  </div>
                  <Progress value={progress} />
                </div>
              )}

              {completedJob ? (
                <>
                  <Button
                    className="w-full gap-2 bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={handleDownload}
                    disabled={downloading}
                  >
                    {downloading ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Download size={16} />
                    )}
                    Download Output
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full gap-2"
                    onClick={() => { setCompletedJob(null); setProgress(0); }}
                  >
                    <Play size={15} />
                    Run Again
                  </Button>
                </>
              ) : (
                <>
                  <Button
                    className="w-full gap-2"
                    disabled={!allRequiredFilled || running}
                    onClick={handleRun}
                  >
                    {running ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Play size={16} />
                    )}
                    Run Pipeline
                  </Button>

                  <Button
                    variant="outline"
                    className="w-full gap-2"
                    disabled={running}
                    onClick={handleRunExisting}
                  >
                    <RefreshCw size={15} />
                    Run with Existing Files
                  </Button>
                </>
              )}
            </CardContent>
          </Card>

          <Card className="bg-muted/40">
            <CardContent className="pt-4 text-xs text-muted-foreground space-y-1.5">
              <p className="font-medium text-foreground">Tips</p>
              <p>Download the <span className="font-medium">Sample</span> button next to each slot to get 5-row example files showing the exact expected format.</p>
              <p>Files are validated server-side. Wrong format will show an error in the job log.</p>
              <p><span className="font-medium">Run with Existing Files</span> re-triggers the pipeline using the last uploaded set.</p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
