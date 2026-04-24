from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.auth import require_admin
from src.api.db import get_conn
from src.api.models import AuditLogEntry, AuditLogListResponse

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/logs", response_model=AuditLogListResponse)
def list_audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    identity: str | None = None,
    method: str | None = None,
    path_contains: str | None = None,
    status_code: int | None = None,
    from_ts: float | None = Query(None, description="Unix start timestamp (inclusive)"),
    to_ts: float | None = Query(None, description="Unix end timestamp (inclusive)"),
    _admin: dict = Depends(require_admin),
) -> AuditLogListResponse:
    conn = get_conn()

    where_parts: list[str] = []
    params: list[object] = []

    if identity:
        where_parts.append("identity = ?")
        params.append(identity)
    if method:
        where_parts.append("method = ?")
        params.append(method.upper())
    if path_contains:
        where_parts.append("path LIKE ?")
        params.append(f"%{path_contains}%")
    if status_code is not None:
        where_parts.append("status_code = ?")
        params.append(status_code)
    if from_ts is not None:
        where_parts.append("ts >= ?")
        params.append(from_ts)
    if to_ts is not None:
        where_parts.append("ts <= ?")
        params.append(to_ts)

    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""

    total = conn.execute(
        f"SELECT COUNT(*) AS cnt FROM audit_log{where_clause}", params
    ).fetchone()["cnt"]

    rows = conn.execute(
        f"SELECT id, ts, client_ip, auth_type, identity, method, path, status_code, duration_ms "
        f"FROM audit_log{where_clause} ORDER BY id DESC LIMIT ? OFFSET ?",
        [*params, limit, offset],
    ).fetchall()

    return AuditLogListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[AuditLogEntry(**dict(row)) for row in rows],
    )


@router.get("/logs/{log_id}", response_model=AuditLogEntry)
def get_audit_log(log_id: int, _admin: dict = Depends(require_admin)) -> AuditLogEntry:
    row = get_conn().execute(
        "SELECT id, ts, client_ip, auth_type, identity, method, path, status_code, duration_ms "
        "FROM audit_log WHERE id = ?",
        (log_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return AuditLogEntry(**dict(row))


@router.delete("/logs/{log_id}")
def delete_audit_log(log_id: int, _admin: dict = Depends(require_admin)) -> dict:
    conn = get_conn()
    result = conn.execute("DELETE FROM audit_log WHERE id = ?", (log_id,))
    conn.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return {"message": f"Deleted audit log {log_id}"}
