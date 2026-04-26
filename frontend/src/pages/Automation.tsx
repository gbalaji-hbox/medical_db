import { useState } from "react";
import { Bot, Check, Copy, Download, Eye, EyeOff } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

function buildBatContent(
  username: string,
  password: string,
  apiBaseUrl: string,
  apiKey: string,
): string {
  // String.raw preserves backslashes literally — no \n / \t escaping needed for bat paths
  return String.raw`@echo off
echo =====================================
echo  DrChrono Automation Runner
echo =====================================

:: ── CONFIGURATION ─────────────────────────────────────────────────────────────
set drchrono_username=${username}
set drchrono_password=${password}
set API_BASE_URL=${apiBaseUrl}
set API_KEY=${apiKey}
:: ─────────────────────────────────────────────────────────────────────────────

:: ── Check Node.js — install if missing ───────────────────────────────────────
where node >nul 2>&1
if errorlevel 1 (
  echo Node.js not found. Installing...
  powershell -Command "Invoke-WebRequest https://nodejs.org/dist/latest-v20.x/node-v20.20.2-x64.msi -OutFile '%TEMP%\node.msi'"
  start /wait msiexec /i "%TEMP%\node.msi" /qn /norestart
  del "%TEMP%\node.msi"
  echo Node.js installed.
)

:: ── Prepare dated output folder on Desktop ────────────────────────────────────
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd"') do set TODAY=%%i
set DESKTOP=%USERPROFILE%\Desktop
set OUT_ROOT=%DESKTOP%\DrChrono_%TODAY%
set RAW_DIR=%OUT_ROOT%\raw
set OUTPUT_DIR=%OUT_ROOT%\output

if not exist "%RAW_DIR%"    mkdir "%RAW_DIR%"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"

:: ── Working directory ─────────────────────────────────────────────────────────
set WORK_DIR=%TEMP%\drchrono_run
if exist "%WORK_DIR%" rmdir /s /q "%WORK_DIR%"
mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"
mkdir output\drchrono

:: ── Download automation script ────────────────────────────────────────────────
echo Downloading automation script...
curl -H "X-Api-Key: %API_KEY%" "%API_BASE_URL%/api/scripts/drchrono-submit.ts" -o drchrono-submit.ts

if not exist drchrono-submit.ts (
  echo ERROR: Script download failed
  pause
  exit /b 1
)

:: ── Install dependency (NO npm init needed) ───────────────────────────────────
echo Installing dependencies...
call npm install @balaji-g42/libretto --yes

if errorlevel 1 (
  echo ERROR: npm install failed
  pause
  exit /b 1
)

:: ── Force Node to see installed modules ───────────────────────────────────────
set NODE_PATH=%WORK_DIR%\node_modules

:: ── Run automation ────────────────────────────────────────────────────────────
echo Starting DrChrono automation...
call npx libretto run drchrono-submit.ts --headless

if errorlevel 1 (
  echo ERROR: Automation failed. Check logs above.
  pause
  exit /b 1
)

:: ── Copy outputs ──────────────────────────────────────────────────────────────
echo Saving files to Desktop...
for %%f in ("%WORK_DIR%\output\drchrono\*.csv") do copy "%%f" "%RAW_DIR%\" >nul
for %%f in ("%WORK_DIR%\output\drchrono\*.xlsx") do copy "%%f" "%OUTPUT_DIR%\" >nul

:: ── Cleanup ───────────────────────────────────────────────────────────────────
del drchrono-submit.ts >nul 2>&1
cd /d "%TEMP%"
rmdir /s /q "%WORK_DIR%"

echo.
echo =====================================
echo  Done!
echo  Raw reports : %RAW_DIR%
echo  Output file : %OUTPUT_DIR%
echo =====================================
pause
`;
}

function downloadBatClientSide(content: string) {
  const blob = new Blob([content], { type: "application/octet-stream" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "run_drchrono.bat";
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

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

function PasswordField({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <Input
        type={show ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pr-9 text-sm"
      />
      <button
        type="button"
        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        onClick={() => setShow((s) => !s)}
      >
        {show ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    </div>
  );
}

function XHIAutomationDetail() {
  const defaultBase = `${window.location.origin}${import.meta.env.BASE_URL}`.replace(/\/$/, "");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [apiBaseUrl, setApiBaseUrl] = useState(defaultBase);
  const [apiKey, setApiKey] = useState("");

  const canDownload = username.trim() && password.trim() && apiBaseUrl.trim() && apiKey.trim();

  function handleDownload() {
    downloadBatClientSide(buildBatContent(username.trim(), password.trim(), apiBaseUrl.trim(), apiKey.trim()));
  }

  const tsScriptUrl = `${apiBaseUrl}${API_BASE.replace(import.meta.env.BASE_URL.replace(/\/$/, ""), "")}/scripts/drchrono-submit.ts`;

  return (
    <div className="space-y-5 mt-4">
      <div className="space-y-1">
        <p className="text-sm font-medium">What it does</p>
        <p className="text-sm text-muted-foreground">
          Downloads reports from DrChrono (Advanced Report, Medication Report, Problem Report),
          sends them to this server for consolidation, then saves the raw CSVs and final
          Excel file to your Desktop under a dated folder.
        </p>
      </div>

      {/* Credentials form */}
      <div className="space-y-3">
        <p className="text-sm font-medium">Configure credentials</p>
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">DrChrono Username</label>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="username@example.com"
              className="text-sm"
            />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">DrChrono Password</label>
            <PasswordField value={password} onChange={setPassword} placeholder="••••••••" />
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">API Base URL</label>
            <div className="flex items-center gap-1.5">
              <Input
                value={apiBaseUrl}
                onChange={(e) => setApiBaseUrl(e.target.value)}
                placeholder="https://your-server.com/emr"
                className="text-sm"
              />
              <CopyButton text={apiBaseUrl} />
            </div>
          </div>
          <div className="space-y-1">
            <label className="text-xs text-muted-foreground">
              API Key{" "}
              <span className="text-muted-foreground/60">(Admin → API Keys)</span>
            </label>
            <PasswordField value={apiKey} onChange={setApiKey} placeholder="Paste your API key" />
          </div>
        </div>
        <p className="text-xs text-muted-foreground">
          Credentials are embedded in the bat file and never sent to this server.
          The bat file runs on the clinic machine only.
        </p>
      </div>

      {/* Download */}
      <div className="flex items-center gap-3 pt-1">
        <Button
          variant="default"
          size="sm"
          className="gap-1.5"
          disabled={!canDownload}
          onClick={handleDownload}
        >
          <Download size={13} />
          Download bat file
        </Button>
        {!canDownload && (
          <p className="text-xs text-muted-foreground">Fill all fields to enable download</p>
        )}
      </div>

      {/* How to use */}
      <div className="rounded-md border bg-muted/40 px-4 py-3 space-y-1">
        <p className="text-xs font-medium">How to use</p>
        <ol className="text-xs text-muted-foreground list-decimal list-inside space-y-0.5">
          <li>Fill the fields above and download the bat file</li>
          <li>Copy it to the clinic Windows machine</li>
          <li>Double-click to run — it installs dependencies and opens DrChrono automatically</li>
          <li>Reports are saved to your Desktop under <code className="font-mono">DrChrono_YYYYMMDD\</code></li>
        </ol>
        <p className="text-xs text-muted-foreground pt-1">
          The bat downloads the latest automation script from{" "}
          <code className="font-mono text-[10px] break-all">{tsScriptUrl}</code>{" "}
          each run, so you always get the latest version.
        </p>
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
