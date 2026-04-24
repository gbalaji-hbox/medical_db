from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from src.api import auth as auth_router
from src.api.auth import get_current_identity
from src.api.audit import AuditMiddleware
from src.api.config import CORS_ORIGINS, RATE_LIMIT_DEFAULT
from src.api.db import init_db
from src.api.job_store import store
from src.api.models import JobStatus
from src.api.routers import cam, cim, hct, mca, ssc, xhi

limiter = Limiter(key_func=get_remote_address, default_limits=[RATE_LIMIT_DEFAULT])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Medical ETL API",
    description=(
        "REST API for triggering and monitoring medical data ETL pipelines.\n\n"
        "**Authentication:** Use `POST /api/auth/login` to get a JWT token, "
        "then pass it as `Authorization: Bearer <token>`. "
        "Alternatively supply an `X-Api-Key` header with a pre-issued API key."
    ),
    version="1.2.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router.router)
for _router in [mca.router, hct.router, ssc.router, cam.router, cim.router, xhi.router]:
    app.include_router(_router)


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/jobs", response_model=list[JobStatus], tags=["system"])
def all_jobs(identity: dict = Depends(get_current_identity)) -> list[JobStatus]:
    return [JobStatus(**j.__dict__) for j in store.all_jobs()]


@app.get("/api/modules", tags=["system"])
def list_modules() -> dict:
    return {
        "mca": {
            "description": "Main patient consolidation: insurance, visits, demographics, copay",
            "required_fields": [
                "patients_by_insurance", "patients_with_visits", "patients_by_diagnosis",
                "patient_list", "appointment_report", "copay_report",
            ],
            "optional_fields": ["services_by_provider"],
        },
        "hct": {
            "description": "Demographics + ICD code grouping, insurance",
            "required_fields": ["patient_demographics", "patient_insurance", "icd_codes"],
            "optional_fields": [],
        },
        "ssc": {
            "description": "Chronic care management: medications + diagnoses",
            "required_fields": ["chronic_management", "diagnosis_codes", "medications"],
            "optional_fields": [],
        },
        "cam": {
            "description": "Registry/problem list comorbidity mapping, provider parsing",
            "required_fields": ["data_new"],
            "optional_fields": [],
        },
        "cim": {
            "description": "Intensive care management",
            "required_fields": ["final_hbox"],
            "optional_fields": [],
        },
        "xhi": {
            "description": "External EMR final report: medications + problem mapping",
            "required_fields": ["emr_report", "medication_report", "problem_report"],
            "optional_fields": [],
        },
    }
