from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.auth import get_current_identity
from src.api.config import MODULE_INPUT_DIR
from src.api.models import JobCreated
from src.api.routers._base import register_sample_routes, register_standard_routes
from src.api.runner import launch
from src.api.validators import validate_upload

MODULE = "mca"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]

# Sample files available for MCA module
MCA_SAMPLE_FILES = [
    "appointment_report_sample.xlsx",
    "copay_report_sample.xlsx",
    "patient_list_sample.xlsx",
    "patients_by_diagnosis_sample.xlsx",
    "patients_by_insurance_sample.xlsx",
    "patients_with_visits_sample.xlsx",
    "services_by_provider_sample.xlsx",
]

router = APIRouter(prefix=f"/api/{MODULE}", tags=[MODULE])
register_standard_routes(router, MODULE)
register_sample_routes(router, MODULE, MCA_SAMPLE_FILES)


@router.post("/process", response_model=JobCreated)
async def process(
    patients_by_insurance: UploadFile = File(...),
    patients_with_visits: UploadFile = File(...),
    patients_by_diagnosis: UploadFile = File(...),
    patient_list: UploadFile = File(...),
    appointment_report: UploadFile = File(...),
    copay_report: UploadFile = File(...),
    services_by_provider: UploadFile = File(None),
    identity: dict = Depends(get_current_identity),
) -> JobCreated:
    """Upload MCA input files (any filename accepted) and run the pipeline."""
    for label, upload, dest in [
        ("patients_by_insurance", patients_by_insurance, "Patients by Insurance.xlsx"),
        ("patients_with_visits", patients_with_visits, "Patients With Visits By Insurance.xlsx"),
        ("patients_by_diagnosis", patients_by_diagnosis, "Patients by Diagnosis or Medication.xlsx"),
        ("appointment_report", appointment_report, "Appointment Report.xlsx"),
        ("copay_report", copay_report, "Copay Report.xlsx"),
    ]:
        content = await validate_upload(upload, label=label)
        (INPUT_DIR / dest).write_bytes(content)

    # Preserve .xls vs .xlsx — the script checks extension at load time
    pl_content = await validate_upload(patient_list, label="patient_list")
    pl_ext = Path(patient_list.filename or "").suffix.lower()
    if pl_ext not in (".xls", ".xlsx"):
        pl_ext = ".xlsx"
    (INPUT_DIR / f"patient-list{pl_ext}").write_bytes(pl_content)

    if services_by_provider:
        svc = await validate_upload(services_by_provider, label="services_by_provider")
        (INPUT_DIR / "Services by Provider Summary.xlsx").write_bytes(svc)

    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(
        job_id=job.job_id, module=MODULE, status=job.status, message="Files saved, job queued"
    )
