"""Unit tests for system and module endpoints (no pipeline execution)."""

import pytest


ALL_MODULES = ["cam", "cim", "hct", "mca", "ssc", "xhi"]


class TestSystemEndpoints:
    def test_health(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_modules_lists_all_six(self, client, admin_headers):
        resp = client.get("/api/modules", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        for m in ALL_MODULES:
            assert m in data

    def test_modules_has_required_fields_key(self, client, admin_headers):
        resp = client.get("/api/modules", headers=admin_headers)
        for module, info in resp.json().items():
            assert "required_fields" in info
            assert "optional_fields" in info

    def test_jobs_list_requires_auth(self, client):
        assert client.get("/api/jobs").status_code == 401

    def test_jobs_list_returns_array(self, client, admin_headers):
        resp = client.get("/api/jobs", headers=admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestModuleEndpointStructure:
    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_get_unknown_job_returns_404(self, client, admin_headers, module):
        resp = client.get(
            f"/api/{module}/jobs/00000000-0000-0000-0000-000000000000",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_download_unknown_job_returns_404(self, client, admin_headers, module):
        resp = client.get(
            f"/api/{module}/jobs/00000000-0000-0000-0000-000000000000/download",
            headers=admin_headers,
        )
        assert resp.status_code == 404

    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_endpoints_require_auth(self, client, module):
        assert client.post(f"/api/{module}/run-existing").status_code == 401
        assert client.get(f"/api/{module}/jobs/fake").status_code == 401
        assert client.get(f"/api/{module}/jobs/fake/download").status_code == 401
