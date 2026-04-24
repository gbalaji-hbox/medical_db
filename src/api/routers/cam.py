from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile

from src.api.auth import get_current_identity
from src.api.config import MODULE_INPUT_DIR
from src.api.models import JobCreated
from src.api.routers._base import register_sample_routes, register_standard_routes
from src.api.runner import launch
from src.api.validators import validate_upload

MODULE = "cam"
INPUT_DIR: Path = MODULE_INPUT_DIR[MODULE]

# Sample files available for CAM module
CAM_SAMPLE_FILES = [
    "data_new_sample.xlsx",
]

router = APIRouter(prefix=f"/api/{MODULE}", tags=[MODULE])
register_standard_routes(router, MODULE)
register_sample_routes(router, MODULE, CAM_SAMPLE_FILES)


@router.post("/process", response_model=JobCreated)
async def process(
    data_new: UploadFile = File(...),
    identity: dict = Depends(get_current_identity),
) -> JobCreated:
    """Upload CAM input file (any filename accepted) and run the pipeline."""
    content = await validate_upload(data_new, label="data_new")
    (INPUT_DIR / "data_new.xlsx").write_bytes(content)
    job = launch(MODULE, submitted_by=identity["username"])
    return JobCreated(
        job_id=job.job_id, module=MODULE, status=job.status, message="File saved, job queued"
    )
