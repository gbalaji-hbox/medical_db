import os
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".creds" / ".env", override=False)

# Use the running interpreter — works on Windows venv and Docker Linux
PYTHON_EXE = sys.executable

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "CHANGE_ME_IN_PRODUCTION")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

if JWT_SECRET_KEY == "CHANGE_ME_IN_PRODUCTION":
    warnings.warn(
        "JWT_SECRET_KEY is using the insecure default value. "
        "Set the JWT_SECRET_KEY environment variable before deploying.",
        stacklevel=1,
    )

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

_cors_raw = os.environ.get("CORS_ORIGINS", "")
CORS_ORIGINS: list[str] = (
    [o.strip() for o in _cors_raw.split(",") if o.strip()] if _cors_raw else ["*"]
)

# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------

# Key file path for Fernet encryption. Auto-generated on first boot.
# In Docker this resolves to /data/encryption.key (same volume as DB).
KEY_FILE = Path(
    os.environ.get(
        "ENCRYPTION_KEY_FILE",
        str(
            Path(os.environ.get("DB_PATH", str(PROJECT_ROOT / ".api_data.db"))).parent
            / "encryption.key"
        ),
    )
)

# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

RATE_LIMIT_DEFAULT = "10/minute"

# ---------------------------------------------------------------------------
# File upload
# ---------------------------------------------------------------------------

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}

# ---------------------------------------------------------------------------
# Output retention & job lifecycle
# ---------------------------------------------------------------------------

OUTPUT_RETENTION_COUNT = 5
# Job row purge window. 0 disables automatic purge so dashboard/job history remains visible.
JOB_TTL_SECONDS = int(os.environ.get("JOB_TTL_SECONDS", "0"))
SUBPROCESS_TIMEOUT = 1800  # 30 min per pipeline

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DB_PATH = Path(os.environ.get("DB_PATH", str(PROJECT_ROOT / ".api_data.db")))

# ---------------------------------------------------------------------------
# Module paths
# ---------------------------------------------------------------------------

# Root path used by SSC and XHI scripts (also hardcoded in their source).
# Set MEDICAL_DB_ROOT=/app on Docker/Linux; defaults to Windows dev path.
MEDICAL_DB_ROOT = os.environ.get("MEDICAL_DB_ROOT", r"D:\Work_Folder\medical_db")

MODULE_SCRIPT = {
    "mca": PROJECT_ROOT / "src" / "MCA" / "scripts" / "main.py",
    "hct": PROJECT_ROOT / "src" / "HCT" / "scripts" / "main.py",
    "ssc": PROJECT_ROOT / "src" / "SSC" / "scripts" / "main.py",
    "cam": PROJECT_ROOT / "src" / "CAM" / "scripts" / "main.py",
    "cim": PROJECT_ROOT / "src" / "CIM" / "scripts" / "main.py",
    "xhi": PROJECT_ROOT / "src" / "XHI" / "scripts" / "main.py",
}

MODULE_INPUT_DIR = {
    "mca": PROJECT_ROOT / "src" / "MCA",
    "hct": PROJECT_ROOT / "src" / "HCT",
    "ssc": PROJECT_ROOT / "src" / "SSC",
    "cam": PROJECT_ROOT / "src" / "CAM",
    "cim": PROJECT_ROOT / "src" / "CIM",
    "xhi": PROJECT_ROOT / "src" / "XHI",
}

MODULE_OUTPUT_DIR = {
    "mca": PROJECT_ROOT / "src" / "MCA" / "output",
    "hct": PROJECT_ROOT / "src" / "HCT" / "output",
    "ssc": PROJECT_ROOT / "src" / "SSC" / "output",
    "cam": PROJECT_ROOT / "src" / "CAM" / "output",
    "cim": PROJECT_ROOT / "src" / "CIM" / "output",
    "xhi": PROJECT_ROOT / "src" / "XHI" / "output",
}

# Sample files directory
SAMPLES_DIR = PROJECT_ROOT / "src" / "samples"

OUTPUT_GLOB = {
    "mca": "MCA_consolidated_*.xlsx*",
    "hct": "HCT_Consolidated_*.xlsx*",
    "ssc": "SSC_consolidated_*.xlsx*",
    "cam": "CAM_consolidated_*.xlsx*",
    "cim": "CIM_consolidated_*.xlsx*",
    "xhi": "XHI_consolidated_*.xlsx*",
}

MODULE_EXTRA_ARGS = {
    "mca": [],
    "hct": ["--base-dir", str(PROJECT_ROOT / "src" / "HCT")],
    "ssc": [],
    "cam": [],
    "cim": [],
    "xhi": [],
}

# Input files deleted after a successful pipeline run (never touches templates)
MODULE_INPUT_FILES = {
    "mca": [
        "Patients by Insurance.xlsx",
        "Patients With Visits By Insurance.xlsx",
        "Patients by Diagnosis or Medication.xlsx",
        "patient-list.xlsx",
        "patient-list.xls",
        "Appointment Report.xlsx",
        "Copay Report.xlsx",
        "Services by Provider Summary.xlsx",
    ],
    "hct": [
        "patient-demographics.xlsx",
        "patient-insurance.xlsx",
        "HCT_Location Wise_Provider Wise_Patient Wise_ICD Codes.xlsx",
    ],
    "ssc": [
        "Chronic Management Patient Details - 20260403_04-55.csv",
        "Patient Diagnosis Code - 20260403_05-19.csv",
        "Patient_Medication - 20260403_06-03.csv",
    ],
    "cam": ["data_new.xlsx"],
    "cim": ["Final_Hbox_3_19_26.xlsx"],
    "xhi": [
        "EMR_Final_Report_final_part.csv",
        "medication_report.csv",
        "problem_report.csv",
    ],
}
