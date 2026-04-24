from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.auth import get_current_identity
from src.api.config import MODULE_INPUT_DIR
from src.api.models import JobCreated
from src.api.routers._base import register_standard_routes
from src.api.runner import launch
from src.api.validators import validate_upload

MODULE = "xhi"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]

_EMR = "EMR_Final_Report_final_part.csv"
_MED = "medication_report.csv"
_PROB = "problem_report.csv"

router = APIRouter(prefix=f"/api/{MODULE}", tags=[MODULE])
register_standard_routes(router, MODULE)


@router.post("/process", response_model=JobCreated)
async def process(
    emr_report: UploadFile = File(...),
    medication_report: UploadFile = File(...),
    problem_report: UploadFile = File(...),
    identity: dict = Depends(get_current_identity),
) -> JobCreated:
    """Upload XHI input files (any filename accepted) and run the pipeline."""
    for label, upload, dest in [
        ("emr_report", emr_report, _EMR),
        ("medication_report", medication_report, _MED),
        ("problem_report", problem_report, _PROB),
    ]:
        content = await validate_upload(upload, label=label)
        (INPUT_DIR / dest).write_bytes(content)

    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(
        job_id=job.job_id, module=MODULE, status=job.status, message="Files saved, job queued"
    )
