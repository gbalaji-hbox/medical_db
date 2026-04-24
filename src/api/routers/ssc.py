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

router = APIRouter(prefix="/api/ssc", tags=["ssc"])
MODULE = "ssc"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]

# SSC script has these exact filenames hardcoded — uploads always overwrite them
_CHRONIC = "Chronic Management Patient Details - 20260403_04-55.csv"
_DIAGNOSIS = "Patient Diagnosis Code - 20260403_05-19.csv"
_MEDICATIONS = "Patient_Medication - 20260403_06-03.csv"


@router.post("/run-existing", response_model=JobCreated)
def run_existing(request: Request, identity: dict = Depends(get_current_identity)):
    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(job_id=job.job_id, module=MODULE, status=job.status,
                      message="Job queued using existing files on disk")


@router.post("/process", response_model=JobCreated)
async def process(
    request: Request,
    chronic_management: UploadFile = File(...),
    diagnosis_codes: UploadFile = File(...),
    medications: UploadFile = File(...),
    identity: dict = Depends(get_current_identity),
):
    """Upload SSC input files (any filename) and run. Files saved with script-expected names."""
    for label, upload, dest in [
        ("chronic_management", chronic_management, _CHRONIC),
        ("diagnosis_codes", diagnosis_codes, _DIAGNOSIS),
        ("medications", medications, _MEDICATIONS),
    ]:
        content = await validate_upload(upload, label=label)
        (INPUT_DIR / dest).write_bytes(content)

    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(job_id=job.job_id, module=MODULE, status=job.status,
                      message="Files saved, job queued")


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
