from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.auth import get_current_identity
from src.api.config import MODULE_INPUT_DIR
from src.api.models import JobCreated
from src.api.routers._base import register_sample_routes, register_standard_routes
from src.api.runner import launch
from src.api.validators import validate_upload

MODULE = "ssc"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]

# SSC script has these exact filenames hardcoded — uploads always overwrite them
_CHRONIC = "Chronic Management Patient Details - 20260403_04-55.csv"
_DIAGNOSIS = "Patient Diagnosis Code - 20260403_05-19.csv"
_MEDICATIONS = "Patient_Medication - 20260403_06-03.csv"

# Sample files available for SSC module
SSC_SAMPLE_FILES = [
    "Chronic_Management_Patient_Details_sample.csv",
    "Patient_Diagnosis_Code_sample.csv",
    "Patient_Medication_sample.csv",
]

router = APIRouter(prefix=f"/api/{MODULE}", tags=[MODULE])
register_standard_routes(router, MODULE)
register_sample_routes(router, MODULE, SSC_SAMPLE_FILES)


@router.post("/process", response_model=JobCreated)
async def process(
    chronic_management: UploadFile = File(...),
    diagnosis_codes: UploadFile = File(...),
    medications: UploadFile = File(...),
    identity: dict = Depends(get_current_identity),
) -> JobCreated:
    """Upload SSC input files (any filename accepted) and run the pipeline."""
    for label, upload, dest in [
        ("chronic_management", chronic_management, _CHRONIC),
        ("diagnosis_codes", diagnosis_codes, _DIAGNOSIS),
        ("medications", medications, _MEDICATIONS),
    ]:
        content = await validate_upload(upload, label=label)
        (INPUT_DIR / dest).write_bytes(content)

    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(
        job_id=job.job_id, module=MODULE, status=job.status, message="Files saved, job queued"
    )
