from typing import Optional

from pydantic import BaseModel


# --- Pipeline job models ---

class JobCreated(BaseModel):
    job_id: str
    module: str
    status: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    module: str
    status: str
    created_at: float
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    returncode: Optional[int] = None
    log: str = ""
    output_file: Optional[str] = None
    submitted_by: Optional[str] = None


# --- Auth models ---

class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ApiKeyRequest(BaseModel):
    name: str
    role: str = "user"


class ApiKeyCreated(BaseModel):
    key_id: str
    key: str
    name: str
    role: str
    message: str


class ApiKeyInfo(BaseModel):
    key_id: str
    name: str
    created_by: str
    created_at: float
    last_used_at: Optional[float] = None
    is_active: int
    role: str
