"""
Shared endpoint logic for all module routers.

Each module router registers the three common endpoints (run-existing, get_job,
download) via register_standard_routes(), then defines only its own /process
endpoint with module-specific file upload fields.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from src.api.auth import get_current_identity
from src.api.crypto import decrypt_to_bytes
from src.api.job_store import store
from src.api.models import JobCreated, JobStatus
from src.api.runner import launch

_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def register_standard_routes(router: APIRouter, module: str) -> None:
    """Attach run-existing, get_job, and download endpoints to a module router."""

    @router.post("/run-existing", response_model=JobCreated)
    def run_existing(identity: dict = Depends(get_current_identity)) -> JobCreated:
        job = launch(module, submitted_by=identity["username"])
        return JobCreated(
            job_id=job.job_id,
            module=module,
            status=job.status,
            message="Job queued using existing files on disk",
        )

    @router.get("/jobs/{job_id}", response_model=JobStatus)
    def get_job(
        job_id: str, identity: dict = Depends(get_current_identity)
    ) -> JobStatus:
        job = store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobStatus(**job.__dict__)

    @router.get("/jobs/{job_id}/download")
    def download(
        job_id: str, identity: dict = Depends(get_current_identity)
    ) -> Response:
        job = store.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        if job.status != "done":
            raise HTTPException(
                status_code=409,
                detail=f"Job not complete (status={job.status})",
            )
        if not job.output_file or not Path(job.output_file).exists():
            raise HTTPException(status_code=404, detail="Output file not found on disk")

        data = decrypt_to_bytes(Path(job.output_file))
        # Strip .enc suffix if present; preserves the original .xlsx extension
        filename = Path(job.output_file).name.removesuffix(".enc")
        return Response(
            content=data,
            media_type=_XLSX_MIME,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
