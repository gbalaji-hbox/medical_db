
from fastapi.testclient import TestClient


def test_audit_logs_access_denied(client: TestClient):
    resp = client.get("/api/audit/logs")
    assert resp.status_code == 401


def test_audit_logs_admin_access(client: TestClient, admin_headers: dict):
    resp = client.get("/api/audit/logs", headers=admin_headers)
    assert resp.status_code == 200

    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)
