from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response

from src.api.auth import get_current_identity
from src.api.config import MODULE_INPUT_DIR
from src.api.crypto import decrypt_to_bytes
from src.api.job_store import store
from src.api.models import JobCreated, JobStatus
from src.api.runner import launch
from src.api.validators import validate_upload

router = APIRouter(prefix="/api/cim", tags=["cim"])
MODULE = "cim"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]


@router.post("/run-existing", response_model=JobCreated)
def run_existing(request: Request, identity: dict = Depends(get_current_identity)):
    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(job_id=job.job_id, module=MODULE, status=job.status,
                      message="Job queued using existing files on disk")


@router.post("/process", response_model=JobCreated)
async def process(
    request: Request,
    final_hbox: UploadFile = File(...),
    identity: dict = Depends(get_current_identity),
):
    """Upload CIM input file (any filename accepted) and run the pipeline."""
    content = await validate_upload(final_hbox, label="final_hbox")
    (INPUT_DIR / "Final_Hbox_3_19_26.xlsx").write_bytes(content)

    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(job_id=job.job_id, module=MODULE, status=job.status,
                      message="File saved, job queued")


@router.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str, identity: dict = Depends(get_current_identity)):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatus(**job.__dict__)


@router.get("/jobs/{job_id}/download")
def download(job_id: str, identity: dict = Depends(get_current_identity)):
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "done":
        raise HTTPException(status_code=409, detail=f"Job not complete (status={job.status})")
    if not job.output_file or not Path(job.output_file).exists():
        raise HTTPException(status_code=404, detail="Output file not found on disk")
    data = decrypt_to_bytes(Path(job.output_file))
    filename = Path(job.output_file).stem
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
