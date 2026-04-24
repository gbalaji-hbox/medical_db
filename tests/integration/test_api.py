"""
Integration tests — require a running server AND existing raw input files on disk.

Usage:
    # Terminal 1: start server
    .venv\\Scripts\\uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --workers 1

    # Terminal 2: run integration tests
    .venv\\Scripts\\pytest tests/integration/ -v -s

    # Or test a single module:
    .venv\\Scripts\\pytest tests/integration/ -v -s -k cam
"""

import time
from pathlib import Path

import httpx
import pytest

BASE_URL = "http://127.0.0.1:8000"
POLL_INTERVAL = 10
MAX_WAIT = 1800

MODULE_INITIAL_WAIT = {
    "cam": 30, "cim": 30, "hct": 60,
    "mca": 120, "ssc": 180, "xhi": 180,
}

ALL_MODULES = ["cam", "cim", "hct", "mca", "ssc", "xhi"]


@pytest.fixture(scope="module")
def http_client():
    with httpx.Client(base_url=BASE_URL, timeout=60.0) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers(http_client):
    resp = http_client.post("/api/auth/login", json={"username": "admin", "password": "HBox@123456!"})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _poll_until_done(client, module: str, job_id: str, initial_wait: int) -> dict:
    time.sleep(initial_wait)
    deadline = time.time() + MAX_WAIT
    while time.time() < deadline:
        status = client.get(f"/api/{module}/jobs/{job_id}", ).json()
        if status["status"] in ("done", "failed"):
            return status
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"{module} job {job_id} did not complete within {MAX_WAIT}s")


class TestHealthAndAuth:
    def test_health(self, http_client):
        assert http_client.get("/api/health").json() == {"status": "ok"}

    def test_protected_requires_auth(self, http_client):
        assert http_client.get("/api/jobs").status_code == 401

    def test_login_and_access(self, http_client, auth_headers):
        assert http_client.get("/api/jobs", headers=auth_headers).status_code == 200


@pytest.mark.parametrize("module", ALL_MODULES)
class TestModulePipeline:
    def test_run_existing_and_download(self, http_client, auth_headers, module):
        # Submit
        resp = http_client.post(f"/api/{module}/run-existing", headers=auth_headers)
        assert resp.status_code == 200, f"Submit failed: {resp.text}"
        job_id = resp.json()["job_id"]

        # 409 before completion
        dl = http_client.get(f"/api/{module}/jobs/{job_id}/download", headers=auth_headers)
        assert dl.status_code == 409

        # Wait for completion
        status = _poll_until_done(http_client, module, job_id, MODULE_INITIAL_WAIT[module])
        assert status["status"] == "done", f"Pipeline failed:\n{status.get('log', '')[-2000:]}"

        # Download
        dl = http_client.get(
            f"/api/{module}/jobs/{job_id}/download",
            headers=auth_headers,
            follow_redirects=True,
        )
        assert dl.status_code == 200
        assert len(dl.content) > 0
        assert "spreadsheetml" in dl.headers.get("content-type", "")

        # 404 for unknown job
        bad = http_client.get(f"/api/{module}/jobs/nonexistent", headers=auth_headers)
        assert bad.status_code == 404
