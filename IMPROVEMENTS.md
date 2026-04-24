# API Improvement Roadmap

This document covers gaps in the current FastAPI implementation across three dimensions: **persistence**, **HIPAA compliance**, and **operational hardening**. Each item includes what is currently missing, why it matters, and a concrete fix.

---

## 1. Job Persistence — Replace In-Memory Store with SQLite

### What is missing

The job store (`src/api/job_store.py`) is an in-memory Python dict. Every server restart silently discards all job records. If uvicorn crashes mid-pipeline, the job status is gone even though the subprocess may still be running or the output file may have been written.

### Why it matters

- Users lose visibility into past runs with no audit trail.
- There is no way to answer "who ran which pipeline, when, with what result."
- A server crash during a long MCA run (which takes 2+ minutes) leaves no record.
- `--workers 1` is required today specifically because the dict is not shared across processes.

### Proposed fix

Replace `JobStore` with SQLite via the standard library `sqlite3`. No new dependencies required.

```python
# src/api/job_store.py (SQLite version)
import sqlite3, threading, time, uuid
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / ".api_jobs.db"

_local = threading.local()

def _conn():
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                module TEXT,
                status TEXT,
                created_at REAL,
                started_at REAL,
                finished_at REAL,
                output_file TEXT,
                log TEXT,
                returncode INTEGER
            )
        """)
        _local.conn.commit()
    return _local.conn
```

Benefits:
- Survives server restarts.
- Supports `--workers 2+` (each worker gets its own SQLite connection via WAL mode).
- Enables a `/api/jobs/history` endpoint for past runs.
- SQLite file can be backed up with a simple file copy.

Enable WAL mode for concurrent access: `PRAGMA journal_mode=WAL;`

---

## 2. HIPAA Compliance Gaps

The pipeline processes **Protected Health Information (PHI)** — patient names, dates of birth, insurance IDs, diagnoses (ICD-10 codes), medications, emergency contacts, and more. The current API has significant HIPAA technical safeguard gaps.

### 2a. No Encryption in Transit (Critical)

**Current state:** The server runs plain HTTP on port 8000. All file uploads (patient Excel/CSV files) and downloaded output files travel over the network unencrypted.

**HIPAA requirement:** 45 CFR §164.312(e)(1) — Implement technical security measures to guard against unauthorized access to PHI transmitted over electronic communications networks.

**Fix — TLS via reverse proxy (recommended):**

Place nginx or Caddy in front of uvicorn. Caddy is the simplest option — it auto-provisions a TLS certificate via Let's Encrypt.

```
# Caddyfile
api.yourclinic.com {
    reverse_proxy 127.0.0.1:8000
}
```

For internal-only deployment (no public domain), use a self-signed certificate or internal CA:

```bash
# Generate self-signed cert (internal use only)
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes

# Run uvicorn with TLS directly (simpler, no proxy needed)
uvicorn src.api.main:app --host 0.0.0.0 --port 8443 \
    --ssl-keyfile key.pem --ssl-certfile cert.pem --workers 1
```

For production, use a certificate from an internal PKI or a proper CA — never deploy with a self-signed cert without browser trust anchors in a clinical environment.

### 2b. No Authentication or Authorization (Critical)

**Current state:** Any process on the network that can reach port 8000 can upload files, trigger pipelines, and download patient data. There is no login, no API key, no session, no role check.

**HIPAA requirement:** 45 CFR §164.312(a)(1) — Implement technical policies and procedures for electronic information systems that maintain PHI to allow access only to authorized persons or software programs.

**Fix — API key authentication (minimal viable):**

```python
# src/api/auth.py
import os
from fastapi import Header, HTTPException

_VALID_KEYS = set(os.environ.get("API_KEYS", "").split(","))

def require_api_key(x_api_key: str = Header(...)):
    if x_api_key not in _VALID_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")
```

Add to every router endpoint:

```python
@router.post("/run-existing", dependencies=[Depends(require_api_key)])
```

Store keys in `.creds/.env` (already git-ignored). Rotate keys per user/application so access can be revoked individually.

For a full deployment, consider OAuth2 with short-lived tokens and role-based access (e.g., only certain users can run MCA but not SSC).

### 2c. No Audit Logging (Critical)

**Current state:** There is no record of who triggered a pipeline, when, from which IP, with which files, or who downloaded the output.

**HIPAA requirement:** 45 CFR §164.312(b) — Implement hardware, software, and/or procedural mechanisms that record and examine activity in information systems that contain or use PHI.

**Fix — Structured access log:**

```python
# src/api/audit.py
import logging, time
from fastapi import Request

audit_log = logging.getLogger("audit")
logging.basicConfig(
    filename="audit.log",
    format='%(asctime)s %(message)s',
    level=logging.INFO
)

async def audit_middleware(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    audit_log.info(
        f"ip={request.client.host} "
        f"method={request.method} "
        f"path={request.url.path} "
        f"status={response.status_code} "
        f"duration={time.time()-start:.2f}s"
    )
    return response
```

Log minimum required fields per HIPAA: timestamp, user identity, type of action, what PHI was accessed, and outcome. Logs must be retained for **6 years**.

### 2d. PHI in Job Logs (Medium Risk)

**Current state:** `job.log` captures full stdout+stderr from the pipeline scripts. MCA scripts print patient IDs, names, and diagnostic information during processing. This log is returned verbatim via `GET /api/{module}/jobs/{job_id}`.

**Fix:**
- Strip or hash patient identifiers from logs before storing in the job record.
- Or: store logs only server-side (file), never return raw log content to the API caller. Return only a log reference ID.
- Minimum: do not include `log` content in the JSON response for completed jobs with PHI.

### 2e. No Encryption at Rest (Medium Risk)

**Current state:** Input Excel/CSV files and output consolidated files are stored on the Windows filesystem in plaintext. The `.creds/.env` file contains multiple EHR system passwords in plaintext (though git-ignored).

**HIPAA requirement:** 45 CFR §164.312(a)(2)(iv) — Encryption and decryption of PHI at rest is an addressable implementation specification (effectively required if a risk analysis identifies it as reasonable).

**Fix options (ordered by effort):**
1. Enable **BitLocker** on the Windows drive where `D:\Work_Folder\` resides. Zero code change, OS-level encryption.
2. Move input/output files to an encrypted volume or folder using Windows EFS.
3. Use Python `cryptography` library to encrypt output files before writing, decrypt before serving downloads.

### 2f. No Input File Validation (Medium Risk)

**Current state:** Uploaded files are written directly to disk with no validation. A malicious actor could upload a file that exploits a vulnerability in openpyxl, Spire.XLS, or pandas during processing.

**Fix:**
- Validate MIME type and file extension before saving.
- Enforce maximum upload file size (e.g., 50 MB).
- Scan uploaded files with an antivirus hook if available.

```python
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB

async def validate_upload(file: UploadFile):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {ext} not allowed")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large")
    await file.seek(0)
```

### 2g. Error Messages May Leak PHI (Low Risk)

**Current state:** If a pipeline fails, the full traceback (which may contain patient names, file paths with patient data, or ICD codes) is returned in `job.log` via the API response.

**Fix:** Return only a sanitized error summary to the caller. Store full logs server-side only.

### 2h. No Rate Limiting (Low Risk)

**Current state:** An authenticated user (once auth is added) or any network-adjacent host today can submit hundreds of pipeline jobs rapidly, triggering repeated processing of PHI files and potentially causing denial of service.

**Fix:** Add rate limiting per client IP using `slowapi`:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/run-existing")
@limiter.limit("5/minute")
def run_existing(request: Request): ...
```

---

## 3. Operational Gaps

### 3a. No Output File Retention Policy

**Current state:** Output files accumulate indefinitely in each module's `output/` directory. Over time this will consume disk space and PHI files will persist longer than necessary.

**HIPAA note:** HIPAA requires retention of health records for at least 6 years from creation date or last effective date. However, these are consolidated *working files*, not the authoritative medical record — confirm with your compliance officer whether the 6-year rule applies.

**Fix:** Add a scheduled cleanup job that deletes output files older than a configurable retention window (e.g., 90 days for working files):

```python
# In config.py
OUTPUT_RETENTION_DAYS = 90

# In a scheduled task (cron / Windows Task Scheduler)
for module_dir in MODULE_OUTPUT_DIR.values():
    for f in module_dir.glob("*.xlsx"):
        age_days = (time.time() - f.stat().st_mtime) / 86400
        if age_days > OUTPUT_RETENTION_DAYS:
            f.unlink()
```

### 3b. Server Does Not Survive Reboots

**Current state:** The uvicorn server must be started manually. A Windows reboot drops the server entirely.

**Fix:** Register uvicorn as a Windows service using NSSM (Non-Sucking Service Manager):

```bat
nssm install MedicalETLAPI "D:\Work_Folder\medical_db\.venv\Scripts\uvicorn.exe"
nssm set MedicalETLAPI AppParameters "src.api.main:app --host 0.0.0.0 --port 8443 --workers 1"
nssm set MedicalETLAPI AppDirectory "D:\Work_Folder\medical_db"
nssm set MedicalETLAPI Start SERVICE_AUTO_START
nssm start MedicalETLAPI
```

### 3c. No Health Monitoring or Alerting

**Current state:** If the server crashes or a pipeline consistently fails, there is no alert.

**Fix:** Add a `/api/metrics` endpoint exposing job success/failure counts. Wire it to a simple uptime monitor (UptimeRobot, Grafana, or even a Windows Task Scheduler ping script).

### 3d. No Input File Cleanup After Processing

**Current state:** Raw uploaded PHI files (patient Excel exports) remain on disk in `src/{MODULE}/` indefinitely after processing. These are unencrypted copies of the source data.

**Fix:** Delete uploaded input files immediately after the pipeline subprocess completes successfully. Keep them on failure for debugging, but move them to a secured, access-controlled quarantine directory rather than leaving them in the open module directory.

### 3e. MCA Subprocess Unicode Crash (Bug — Fixed)

**What happened:** MCA `main.py` uses emoji characters (`❌`, `✅`) in its print statements. When run as a subprocess on Windows with the default cp1252 encoding, these characters cause a `UnicodeEncodeError` that masks the real error underneath.

**Fix applied:** `src/api/runner.py` now passes `-X utf8` to the Python interpreter invocation:
```python
cmd = [PYTHON_EXE, "-X", "utf8", script] + extra_args
```
This forces UTF-8 mode at the interpreter level — more reliable than `PYTHONIOENCODING` on Windows, where the child process may inherit the terminal's cp1252 encoding regardless of environment variables.

### 3f. Server Process Management on Windows

**Problem:** `pkill` (Unix) does not reliably terminate processes on Windows/Git Bash. Running `pkill -f uvicorn` appears to succeed but leaves the old process alive on port 8000. Any subsequent server start silently fails to bind the port, so the old code (without fixes) keeps serving requests.

**Fix:** Always stop the server using Windows `taskkill`:
```powershell
# Find PID
netstat -ano | findstr ":8000"
# Kill it
taskkill /PID <pid> /F
```
Or wrap server management in a PowerShell script that handles the PID lifecycle. Consider using NSSM (see §3b) which handles restarts cleanly via the Windows service manager.

### 3f. No Swagger/OpenAPI Auth Integration

**Current state:** The auto-generated Swagger UI at `/docs` lets anyone explore and call all endpoints — useful for development, dangerous if exposed on a network.

**Fix:** Disable Swagger in production (`app = FastAPI(docs_url=None, redoc_url=None)`) or add HTTP Basic auth gating to the docs route.

### 3g. Hardcoded SSC/XHI Input Filenames

**Current state:** SSC and XHI scripts have filenames with embedded timestamps hardcoded (`Chronic Management Patient Details - 20260403_04-55.csv`). If the source system generates files with a new timestamp, the pipeline silently reads the old file.

**Fix (without changing existing scripts):** Add a pre-flight check in the router that verifies the expected files exist before launching the job:

```python
@router.post("/run-existing")
def run_existing():
    missing = [f for f in EXPECTED_FILES if not (INPUT_DIR / f).exists()]
    if missing:
        raise HTTPException(400, f"Missing input files: {missing}")
    job = launch(MODULE)
    ...
```

---

## Summary Table

| Gap | Severity | HIPAA Relevant | Effort |
|---|---|---|---|
| No TLS/HTTPS | **Critical** | Yes (§164.312(e)) | Low (Caddy/nginx) |
| No authentication | **Critical** | Yes (§164.312(a)) | Low (API keys) |
| No audit logging | **Critical** | Yes (§164.312(b)) | Low |
| SQLite job store | High | Indirectly | Low |
| PHI in job logs | Medium | Yes | Medium |
| No encryption at rest | Medium | Yes (§164.312(a)(2)(iv)) | Low (BitLocker) |
| Input file validation | Medium | No | Low |
| No retention policy | Medium | Yes | Low |
| Rate limiting | Low | No | Low |
| Server auto-start | Low | No | Low |
| No input file cleanup | Medium | Yes | Low |
| Swagger exposure | Low | No | Trivial |
| SSC/XHI filename check | Low | No | Trivial |

**Minimum to be HIPAA-ready:** Items 1–3 (TLS, auth, audit logging) plus BitLocker for at-rest encryption. Everything else is defense-in-depth or operational hardening.

---

## Recommended Implementation Order

1. **Enable BitLocker** on the `D:\` drive — zero code, immediate at-rest protection.
2. **Add TLS** — run uvicorn with `--ssl-keyfile`/`--ssl-certfile` or put Caddy in front.
3. **Add API key auth** — add `src/api/auth.py` and `Depends(require_api_key)` to all routers.
4. **Add audit logging** — add middleware to `main.py`, log to a file retained for 6 years.
5. **Migrate to SQLite job store** — replace `job_store.py`, enable `--workers 2`.
6. **Add input file cleanup** — delete raw uploads after successful pipeline run.
7. **Register as Windows service** — NSSM for auto-restart on reboot.
8. **Add file validation** — MIME type and size checks on all upload endpoints.
9. **Strip PHI from logs** — sanitize job.log before returning via API.
10. **Add retention policy** — scheduled cleanup of old output files.
