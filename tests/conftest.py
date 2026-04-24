"""
Shared pytest fixtures and environment setup.

IMPORTANT: env vars must be set at module level — before any src.api.* import —
because config.py and crypto.py read them at import time (not inside functions).
"""

import os
import tempfile
from pathlib import Path

# ── Set test paths before any src.api imports ─────────────────────────────────
_TMP = Path(tempfile.mkdtemp(prefix="medical_db_test_"))
os.environ.setdefault("DB_PATH", str(_TMP / "test.db"))
os.environ.setdefault("ENCRYPTION_KEY_FILE", str(_TMP / "test_enc.key"))
os.environ.setdefault("JWT_SECRET_KEY", "pytest-secret-not-for-production")
# ─────────────────────────────────────────────────────────────────────────────

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Single TestClient for the full session — startup event runs init_db()."""
    from src.api.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client: TestClient) -> str:
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "HBox@123456!"})
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="session")
def admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def fresh_db():
    """In-memory SQLite connection for pure migration/DB unit tests."""
    import sqlite3
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    yield conn
    conn.close()
