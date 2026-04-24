"""
Shared endpoint logic for all module routers.

Each module router registers the three common endpoints (run-existing, get_job,
download) via register_standard_routes(), then defines only its own /process
endpoint with module-specific file upload fields.

Sample file endpoints are registered via register_sample_routes() to allow
downloading sample input files for each module.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from src.api.auth import get_current_identity
from src.api.config import SAMPLES_DIR
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


# MIME types for sample files
_SAMPLE_MIME_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
}


def register_sample_routes(router: APIRouter, module: str, sample_files: list[str]) -> None:
    """
    Attach sample file endpoints to a module router.
    
    Args:
        router: The APIRouter to attach routes to.
        module: The module name (e.g., 'mca', 'hct').
        sample_files: List of sample file names available for this module.
    """

    @router.get("/samples", tags=["samples"])
    def list_samples(identity: dict = Depends(get_current_identity)) -> dict:
        """List all available sample files for this module."""
        return {
            "module": module,
            "samples": sample_files,
        }

    @router.get("/samples/{sample_name}", tags=["samples"])
    def download_sample(
        sample_name: str, identity: dict = Depends(get_current_identity)
    ) -> Response:
        """Download a specific sample file for this module."""
        if sample_name not in sample_files:
            raise HTTPException(
                status_code=404,
                detail=f"Sample file '{sample_name}' not found for module '{module}'",
            )

        sample_path = SAMPLES_DIR / module.upper() / sample_name
        if not sample_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Sample file not found on disk: {sample_name}",
            )

        # Determine media type from file extension
        ext = sample_path.suffix.lower()
        media_type = _SAMPLE_MIME_TYPES.get(ext, "application/octet-stream")

        # Read file content
        data = sample_path.read_bytes()

        return Response(
            content=data,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{sample_name}"'},
        )
