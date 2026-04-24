from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.auth import get_current_identity
from src.api.config import MODULE_INPUT_DIR
from src.api.models import JobCreated
from src.api.routers._base import register_standard_routes
from src.api.runner import launch
from src.api.validators import validate_upload

MODULE = "hct"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]

_ICD = "HCT_Location Wise_Provider Wise_Patient Wise_ICD Codes.xlsx"

router = APIRouter(prefix=f"/api/{MODULE}", tags=[MODULE])
register_standard_routes(router, MODULE)


@router.post("/process", response_model=JobCreated)
async def process(
    patient_demographics: UploadFile = File(...),
    patient_insurance: UploadFile = File(...),
    icd_codes: UploadFile = File(...),
    identity: dict = Depends(get_current_identity),
) -> JobCreated:
    """Upload HCT input files (any filename accepted) and run the pipeline."""
    for label, upload, dest in [
        ("patient_demographics", patient_demographics, "patient-demographics.xlsx"),
        ("patient_insurance", patient_insurance, "patient-insurance.xlsx"),
        ("icd_codes", icd_codes, _ICD),
    ]:
        content = await validate_upload(upload, label=label)
        (INPUT_DIR / dest).write_bytes(content)

    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(
        job_id=job.job_id, module=MODULE, status=job.status, message="Files saved, job queued"
    )
