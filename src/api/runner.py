"""
Pipeline runner: launches each module script in a daemon thread,
captures output, applies PHI scrubbing, encrypts the output file,
enforces retention policy, and cleans up input files.
"""

import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from src.api.config import (
    JOB_TTL_SECONDS,
    MEDICAL_DB_ROOT,
    MODULE_EXTRA_ARGS,
    MODULE_OUTPUT_DIR,
    MODULE_SCRIPT,
    OUTPUT_GLOB,
    PROJECT_ROOT,
    PYTHON_EXE,
    SUBPROCESS_TIMEOUT,
)
from src.api.crypto import encrypt_file
from src.api.job_store import Job, store
from src.api.log_sanitizer import sanitize_log
from src.api.retention import cleanup_inputs, enforce_output_retention

# Per-module lock — serialises concurrent requests to the same module.
# Critical for SSC/XHI which have hardcoded input file paths.
_module_locks: dict[str, threading.Lock] = {m: threading.Lock() for m in MODULE_SCRIPT}

# Whitelist of env vars passed to subprocess — never leak full os.environ secrets
_SUBPROCESS_ENV_KEYS = {
    "PATH", "SYSTEMROOT", "TEMP", "TMP", "HOME", "LANG", "LC_ALL",
    "PYTHONPATH", "VIRTUAL_ENV",
}


def _build_env() -> dict[str, str]:
    """Build a minimal env for subprocess: whitelisted vars + MEDICAL_DB_ROOT."""
    env = {k: v for k, v in os.environ.items() if k in _SUBPROCESS_ENV_KEYS}
    env["MEDICAL_DB_ROOT"] = MEDICAL_DB_ROOT
    return env


def find_latest_output(module: str, after: float) -> Optional[str]:
    """Return the path of the newest output file created at or after `after`."""
    output_dir = MODULE_OUTPUT_DIR[module]
    pattern = OUTPUT_GLOB[module]
    candidates = [p for p in output_dir.glob(pattern) if p.stat().st_mtime >= after]
    if not candidates:
        # Fallback: absolute latest (handles filesystem mtime rounding)
        all_files = sorted(output_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        return str(all_files[0]) if all_files else None
    return str(sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0])


def _run(job: Job) -> None:
    script = str(MODULE_SCRIPT[job.module])
    extra_args = MODULE_EXTRA_ARGS.get(job.module, [])
    cmd = [PYTHON_EXE, script] + extra_args

    with _module_locks[job.module]:
        job.status = "running"
        job.started_at = time.time()
        store.update(job)

        run_start = time.time()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
                cwd=str(PROJECT_ROOT),
                env=_build_env(),
            )
            raw_log = result.stdout + ("\n" + result.stderr if result.stderr else "")
            job.log = sanitize_log(raw_log)
            job.returncode = result.returncode

            if result.returncode == 0:
                job.status = "done"
                output_path = find_latest_output(job.module, after=run_start)
                if output_path:
                    enc_path = encrypt_file(Path(output_path))
                    job.output_file = str(enc_path)
                enforce_output_retention(job.module)
                cleanup_inputs(job.module)
            else:
                job.status = "failed"
                logger.error(
                    "[%s] job %s failed (rc=%s):\n%s",
                    job.module, job.job_id, result.returncode,
                    (result.stdout + "\n" + result.stderr).strip(),
                )

        except subprocess.TimeoutExpired as exc:
            job.status = "failed"
            job.returncode = -1
            out = exc.stdout or ""
            err = exc.stderr or ""
            job.log = sanitize_log(f"TIMEOUT after {SUBPROCESS_TIMEOUT}s\n{out}\n{err}")

        except OSError as exc:
            job.status = "failed"
            job.returncode = -1
            job.log = f"OS error launching pipeline: {exc}"

        except Exception as exc:  # noqa: BLE001 — last-resort catch; type logged
            job.status = "failed"
            job.returncode = -1
            job.log = f"Unexpected runner error: {type(exc).__name__}: {exc}"

        finally:
            job.finished_at = time.time()
            store.update(job)
            if JOB_TTL_SECONDS > 0:
                store.purge_old(JOB_TTL_SECONDS)


def launch(module: str, submitted_by: str = "unknown") -> Job:
    """Create a job record and execute the pipeline in a daemon thread."""
    job = store.create(module, submitted_by=submitted_by)
    thread = threading.Thread(target=_run, args=(job,), daemon=True)
    thread.start()
    return job
