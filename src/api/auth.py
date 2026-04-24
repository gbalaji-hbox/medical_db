"""
Authentication: JWT (Bearer token) + API key (X-Api-Key header).
Either method is accepted on all protected endpoints.

Routes:
  POST /api/auth/login           — username/password → access + refresh tokens
  POST /api/auth/refresh         — refresh token → new access token
  POST /api/auth/keys            — (admin) create API key
  GET  /api/auth/keys            — (admin) list API keys
  DELETE /api/auth/keys/{key_id} — (admin) revoke API key
"""

import hashlib
import secrets
import time
import uuid
from typing import Optional

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from src.api.config import (
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_REFRESH_TOKEN_EXPIRE_DAYS,
    JWT_SECRET_KEY,
)
from src.api.db import get_conn, get_db
from src.api.models import (
    ApiKeyCreated,
    ApiKeyInfo,
    ApiKeyRequest,
    LoginRequest,
    Token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-Api-Key", auto_error=False, scheme_name="ApiKey")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _make_token(data: dict, expire_seconds: int) -> str:
    payload = {**data, "exp": time.time() + expire_seconds, "iat": time.time()}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# FastAPI dependency — accepts JWT or API key
# ---------------------------------------------------------------------------


async def get_current_identity(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
    api_key: Optional[str] = Security(_api_key_header),
) -> dict:
    """
    Returns {"type": "jwt"|"api_key", "username": str, "role": str}.
    Raises 401 if neither credential is valid.
    """
    conn = get_conn()

    # --- Try JWT Bearer token ---
    if creds and creds.scheme.lower() == "bearer":
        payload = _decode_token(creds.credentials)
        if payload and payload.get("type") == "access":
            user = conn.execute(
                "SELECT role, is_active FROM users WHERE username = ?",
                (payload["sub"],),
            ).fetchone()
            if user and user["is_active"]:
                identity = {
                    "type": "jwt",
                    "username": payload["sub"],
                    "role": user["role"],
                }
                request.state.identity = identity
                return identity

    # --- Try API key ---
    if api_key:
        key_hash = _hash_api_key(api_key)
        record = conn.execute(
            "SELECT key_id, name, role, is_active FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        ).fetchone()
        if record and record["is_active"]:
            conn.execute(
                "UPDATE api_keys SET last_used_at = ? WHERE key_id = ?",
                (time.time(), record["key_id"]),
            )
            conn.commit()
            identity = {
                "type": "api_key",
                "username": record["name"],
                "role": record["role"],
            }
            request.state.identity = identity
            return identity

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(identity: dict = Depends(get_current_identity)) -> dict:
    if identity.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return identity


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------


@router.post("/login", response_model=Token, summary="Login with username and password")
def login(body: LoginRequest):
    conn = get_conn()
    row = conn.execute(
        "SELECT hashed_password, role, is_active FROM users WHERE username = ?",
        (body.username,),
    ).fetchone()
    if not row or not row["is_active"] or not _verify_password(body.password, row["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    access = _make_token(
        {"sub": body.username, "role": row["role"], "type": "access"},
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    refresh = _make_token(
        {"sub": body.username, "type": "refresh"},
        JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    return Token(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token, summary="Refresh access token")
def refresh_token(body: dict):
    token = body.get("refresh_token", "")
    payload = _decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    conn = get_conn()
    row = conn.execute(
        "SELECT role, is_active FROM users WHERE username = ?",
        (payload["sub"],),
    ).fetchone()
    if not row or not row["is_active"]:
        raise HTTPException(status_code=401, detail="User not found or disabled")

    access = _make_token(
        {"sub": payload["sub"], "role": row["role"], "type": "access"},
        JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    new_refresh = _make_token(
        {"sub": payload["sub"], "type": "refresh"},
        JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    )
    return Token(
        access_token=access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/keys", response_model=ApiKeyCreated, summary="Create API key (admin only)")
def create_api_key(body: ApiKeyRequest, identity: dict = Depends(require_admin)):
    raw_key = secrets.token_urlsafe(32)
    key_hash = _hash_api_key(raw_key)
    key_id = str(uuid.uuid4())
    conn = get_conn()
    conn.execute(
        "INSERT INTO api_keys (key_id, key_hash, name, created_by, created_at, role) VALUES (?,?,?,?,?,?)",
        (key_id, key_hash, body.name, identity["username"], time.time(), body.role),
    )
    conn.commit()
    return ApiKeyCreated(
        key_id=key_id,
        key=raw_key,
        name=body.name,
        role=body.role,
        message="Store this key — it will not be shown again",
    )


@router.get("/keys", response_model=list[ApiKeyInfo], summary="List API keys (admin only)")
def list_api_keys(identity: dict = Depends(require_admin)):
    conn = get_conn()
    rows = conn.execute(
        "SELECT key_id, name, created_by, created_at, last_used_at, is_active, role FROM api_keys ORDER BY created_at DESC"
    ).fetchall()
    return [ApiKeyInfo(**dict(r)) for r in rows]


@router.delete("/keys/{key_id}", summary="Revoke API key (admin only)")
def revoke_api_key(key_id: str, identity: dict = Depends(require_admin)):
    conn = get_conn()
    result = conn.execute(
        "UPDATE api_keys SET is_active = 0 WHERE key_id = ?", (key_id,)
    )
    conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Key not found")
    return {"message": f"Key {key_id} revoked"}
