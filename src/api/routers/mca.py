import shutil
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

router = APIRouter(prefix="/api/mca", tags=["mca"])
MODULE = "mca"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]


@router.post("/run-existing", response_model=JobCreated)
def run_existing(request: Request, identity: dict = Depends(get_current_identity)):
    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(job_id=job.job_id, module=MODULE, status=job.status,
                      message="Job queued using existing files on disk")


@router.post("/process", response_model=JobCreated)
async def process(
    request: Request,
    patients_by_insurance: UploadFile = File(...),
    patients_with_visits: UploadFile = File(...),
    patients_by_diagnosis: UploadFile = File(...),
    patient_list: UploadFile = File(...),
    appointment_report: UploadFile = File(...),
    copay_report: UploadFile = File(...),
    services_by_provider: UploadFile = File(None),
    identity: dict = Depends(get_current_identity),
):
    """Upload MCA input files (any filename accepted) and run the pipeline."""
    # Validate all uploads
    uploads_raw = {
        "patients_by_insurance": (patients_by_insurance, "Patients by Insurance.xlsx"),
        "patients_with_visits": (patients_with_visits, "Patients With Visits By Insurance.xlsx"),
        "patients_by_diagnosis": (patients_by_diagnosis, "Patients by Diagnosis or Medication.xlsx"),
        "appointment_report": (appointment_report, "Appointment Report.xlsx"),
        "copay_report": (copay_report, "Copay Report.xlsx"),
    }

    for label, (upload, dest_name) in uploads_raw.items():
        content = await validate_upload(upload, label=label)
        (INPUT_DIR / dest_name).write_bytes(content)

    # patient_list: preserve .xls vs .xlsx extension
    pl_content = await validate_upload(patient_list, label="patient_list")
    pl_ext = Path(patient_list.filename or "").suffix.lower()
    if pl_ext not in (".xls", ".xlsx"):
        pl_ext = ".xlsx"
    (INPUT_DIR / f"patient-list{pl_ext}").write_bytes(pl_content)

    if services_by_provider:
        svc_content = await validate_upload(services_by_provider, label="services_by_provider")
        (INPUT_DIR / "Services by Provider Summary.xlsx").write_bytes(svc_content)

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
    filename = Path(job.output_file).stem  # strip .enc if present
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
