import { useState } from "react";
import { Bot, Check, Copy, Download, Terminal } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  MODULES,
  MODULE_LABELS,
  MODULE_CLINIC_NAMES,
  MODULE_DESCRIPTIONS,
  type Module,
} from "@/api/types";
import { API_BASE } from "@/api/client";

// Only XHI has automation for now
const AUTOMATION_AVAILABLE: Partial<Record<Module, true>> = { xhi: true };

const MODULE_COLORS: Record<string, string> = {
  mca: "#3b82f6",
  hct: "#10b981",
  ssc: "#f59e0b",
  cam: "#8b5cf6",
  cim: "#ef4444",
  xhi: "#ec4899",
};

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  function handleCopy() {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }
  return (
    <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={handleCopy}>
      {copied ? <Check size={13} className="text-emerald-500" /> : <Copy size={13} />}
    </Button>
  );
}

function XHIAutomationDetail() {
  const batUrl  = `${window.location.origin}${API_BASE}/scripts/run_drchrono.bat`;
  const curlCmd = `curl -s -H "X-Api-Key: YOUR_API_KEY" "${batUrl}" -o run_drchrono.bat && run_drchrono.bat`;

  return (
    <div className="space-y-4 mt-4">
      <div className="space-y-1">
        <p className="text-sm font-medium">What it does</p>
        <p className="text-sm text-muted-foreground">
          Downloads reports from DrChrono (Advanced Report, Medication Report, Problem Report),
          sends them to this server for consolidation, then saves the raw CSVs and final
          Excel file to your Desktop under a dated folder.
        </p>
      </div>

      <div className="space-y-1">
        <p className="text-sm font-medium">Requirements</p>
        <ul className="text-sm text-muted-foreground list-disc list-inside space-y-0.5">
          <li>Windows machine with Node.js installed (or the bat will install it)</li>
          <li>DrChrono credentials and your API key — fill them in the bat file</li>
        </ul>
      </div>

      <div className="space-y-2">
        <p className="text-sm font-medium flex items-center gap-1.5">
          <Terminal size={13} />
          Run this command once to download the automation
        </p>
        <div className="flex items-center gap-2 rounded-md border bg-muted px-3 py-2">
          <code className="flex-1 text-xs font-mono break-all">{curlCmd}</code>
          <CopyButton text={curlCmd} />
        </div>
        <p className="text-xs text-muted-foreground">
          Replace <code className="text-xs font-mono">YOUR_API_KEY</code> with a key from{" "}
          <span className="font-medium">Admin → API Keys</span>. The bat file stays on your
          machine — run it anytime to re-pull and execute the latest automation.
        </p>
      </div>

      <div className="flex items-center gap-2">
        <a href={`${API_BASE}/scripts/run_drchrono.bat`} target="_blank" rel="noreferrer">
          <Button variant="outline" size="sm" className="gap-1.5">
            <Download size={13} />
            Download bat file
          </Button>
        </a>
      </div>
    </div>
  );
}

function ModuleAutomationCard({ module, isSelected, onClick }: {
  module: Module;
  isSelected: boolean;
  onClick: () => void;
}) {
  const hasAutomation = !!AUTOMATION_AVAILABLE[module];
  const color = MODULE_COLORS[module] ?? "#6b7280";

  return (
    <button
      onClick={onClick}
      className={`relative w-full flex items-center gap-2.5 px-3 py-2.5 rounded-md text-left transition-colors ${
        isSelected ? "bg-accent text-accent-foreground" : "hover:bg-accent/50"
      }`}
    >
      {isSelected && (
        <span className="absolute left-0 top-1 bottom-1 w-0.75 rounded-r-lg" style={{ background: color }} />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1">
          <span className="font-semibold text-sm">{MODULE_LABELS[module]}</span>
          {hasAutomation ? (
            <Badge variant="success" className="text-[10px] px-1.5 py-0 h-4 leading-none gap-0.5">
              <Bot size={9} />
              Auto
            </Badge>
          ) : (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0 h-4 leading-none text-muted-foreground">
              Manual
            </Badge>
          )}
        </div>
        <p className="text-xs text-muted-foreground truncate mt-0.5">{MODULE_CLINIC_NAMES[module]}</p>
      </div>
    </button>
  );
}

function AutomationDetail({ module }: { module: Module }) {
  const hasAutomation = !!AUTOMATION_AVAILABLE[module];

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold">
              {MODULE_LABELS[module]} — {MODULE_CLINIC_NAMES[module]}
            </h2>
            {hasAutomation && (
              <Badge variant="success" className="gap-1">
                <Bot size={11} />
                Automation Available
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">{MODULE_DESCRIPTIONS[module]}</p>
        </div>
      </div>

      <Card>
        <CardHeader className="pb-2 pt-4">
          <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Automation
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-4">
          {hasAutomation ? (
            module === "xhi" ? <XHIAutomationDetail /> : null
          ) : (
            <div className="flex items-center gap-2 text-muted-foreground text-sm py-2">
              <Bot size={15} />
              No automation available for this clinic yet. Reports must be uploaded manually.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function AutomationPage() {
  const [selected, setSelected] = useState<Module>("xhi");

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Automation</h1>
        <p className="text-muted-foreground text-sm mt-1">
          Headless report extraction — runs on the clinic machine, consolidates via this server
        </p>
      </div>

      <div className="grid lg:grid-cols-[220px_1fr] gap-6 items-start">
        {/* Sidebar */}
        <Card className="lg:sticky lg:top-6">
          <CardHeader className="pb-1 pt-3 px-3">
            <CardTitle className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Clinics
            </CardTitle>
          </CardHeader>
          <CardContent className="px-2 pb-3">
            {MODULES.map((m) => (
              <ModuleAutomationCard
                key={m}
                module={m}
                isSelected={m === selected}
                onClick={() => setSelected(m)}
              />
            ))}
          </CardContent>
        </Card>

        {/* Detail */}
        <AutomationDetail module={selected} />
      </div>
    </div>
  );
}
