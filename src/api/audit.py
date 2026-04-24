"""
ASGI middleware that writes one row per request to the audit_log SQLite table.
Identity is captured from request.state.identity, which is set by the
get_current_identity dependency after successful auth.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.api.db import get_conn


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start) * 1000

        identity = getattr(request.state, "identity", None)
        try:
            conn = get_conn()
            conn.execute(
                """INSERT INTO audit_log
                   (ts, client_ip, auth_type, identity, method, path, status_code, duration_ms)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (
                    time.time(),
                    request.client.host if request.client else None,
                    identity["type"] if identity else None,
                    identity["username"] if identity else None,
                    request.method,
                    str(request.url.path),
                    response.status_code,
                    round(duration_ms, 2),
                ),
            )
            conn.commit()
        except Exception:
            pass  # Never let audit failure break the response

        return response
