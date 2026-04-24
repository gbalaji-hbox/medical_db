from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.auth import get_current_identity
from src.api.config import MODULE_INPUT_DIR
from src.api.models import JobCreated
from src.api.routers._base import register_sample_routes, register_standard_routes
from src.api.runner import launch
from src.api.validators import validate_upload

MODULE = "hct"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]

_ICD = "HCT_Location Wise_Provider Wise_Patient Wise_ICD Codes.xlsx"

# Sample files available for HCT module
HCT_SAMPLE_FILES = [
    "HCT_Location_Wise_Provider_Wise_Patient_Wise_ICD_Codes_sample.xlsx",
    "patient-demographics_sample.xlsx",
    "patient-insurance_sample.xlsx",
]

router = APIRouter(prefix=f"/api/{MODULE}", tags=[MODULE])
register_standard_routes(router, MODULE)
register_sample_routes(router, MODULE, HCT_SAMPLE_FILES)


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
