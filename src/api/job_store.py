"""
SQLite-backed job store. Replaces the previous in-memory dict.

Same public interface as the original so runner.py needs no structural changes.
Survives server restarts; safe for --workers > 1 via WAL mode.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Optional

from src.api.db import get_conn


@dataclass
class Job:
    job_id: str
    module: str
    status: str
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    output_file: Optional[str] = None
    log: str = ""
    returncode: Optional[int] = None
    submitted_by: str = "unknown"


def _row_to_job(row) -> Job:
    return Job(
        job_id=row["job_id"],
        module=row["module"],
        status=row["status"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        finished_at=row["finished_at"],
        output_file=row["output_file"],
        log=row["log"] or "",
        returncode=row["returncode"],
        submitted_by=row["submitted_by"] or "unknown",
    )


class JobStore:
    def create(self, module: str, submitted_by: str = "unknown") -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            module=module,
            status="queued",
            created_at=time.time(),
            submitted_by=submitted_by,
        )
        conn = get_conn()
        conn.execute(
            """INSERT INTO jobs
               (job_id, module, status, created_at, log, submitted_by)
               VALUES (?,?,?,?,?,?)""",
            (job.job_id, job.module, job.status, job.created_at, "", submitted_by),
        )
        conn.commit()
        return job

    def get(self, job_id: str) -> Optional[Job]:
        row = get_conn().execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return _row_to_job(row) if row else None

    def update(self, job: Job) -> None:
        conn = get_conn()
        conn.execute(
            """UPDATE jobs SET
               status=?, started_at=?, finished_at=?,
               output_file=?, log=?, returncode=?
               WHERE job_id=?""",
            (
                job.status, job.started_at, job.finished_at,
                job.output_file, job.log, job.returncode,
                job.job_id,
            ),
        )
        conn.commit()

    def all_jobs(self) -> list[Job]:
        rows = get_conn().execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
        return [_row_to_job(r) for r in rows]

    def purge_old(self, ttl: float) -> None:
        cutoff = time.time() - ttl
        conn = get_conn()
        conn.execute("DELETE FROM jobs WHERE created_at < ? AND status IN ('done','failed')", (cutoff,))
        conn.commit()


# Singleton
store = JobStore()
