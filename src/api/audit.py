"""
ASGI middleware that writes one row per request to the audit_log SQLite table.
Identity is captured from request.state.identity, set by get_current_identity
after successful auth. Audit failures are logged but never break the response.
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.api.db import get_conn

logger = logging.getLogger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)

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
                    duration_ms,
                ),
            )
            conn.commit()
        except Exception as exc:  # noqa: BLE001
            # Audit failure must not break the HTTP response; log for ops visibility
            logger.warning("Audit log write failed: %s", exc)

        return response
