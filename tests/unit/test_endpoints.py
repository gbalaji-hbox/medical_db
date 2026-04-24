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


class TestSampleEndpoints:
    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_list_samples_requires_auth(self, client, module):
        resp = client.get(f"/api/{module}/samples")
        assert resp.status_code == 401

    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_download_sample_requires_auth(self, client, module):
        resp = client.get(f"/api/{module}/samples/nonexistent.xlsx")
        assert resp.status_code == 401

    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_list_samples_returns_structure(self, client, admin_headers, module):
        resp = client.get(f"/api/{module}/samples", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["module"] == module
        assert isinstance(data["samples"], list)

    def test_cam_list_samples(self, client, admin_headers):
        resp = client.get("/api/cam/samples", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "data_new_sample.xlsx" in data["samples"]

    def test_mca_list_samples(self, client, admin_headers):
        resp = client.get("/api/mca/samples", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "appointment_report_sample.xlsx" in data["samples"]
        assert "copay_report_sample.xlsx" in data["samples"]
        assert "patient_list_sample.xlsx" in data["samples"]

    def test_download_known_sample_ok(self, client, admin_headers):
        resp = client.get("/api/cam/samples/data_new_sample.xlsx", headers=admin_headers)
        assert resp.status_code == 200
        assert len(resp.content) > 0
        assert "spreadsheetml" in resp.headers.get("content-type", "")

    @pytest.mark.parametrize("module", ALL_MODULES)
    def test_download_unknown_sample_returns_404(self, client, admin_headers, module):
        resp = client.get(f"/api/{module}/samples/fake-file.xlsx", headers=admin_headers)
        assert resp.status_code == 404

    def test_download_sample_missing_on_disk_returns_404(self, client, admin_headers, tmp_path):
        from src.api.routers import _base as base_mod
        original = base_mod.SAMPLES_DIR
        try:
            base_mod.SAMPLES_DIR = tmp_path
            resp = client.get("/api/cam/samples/data_new_sample.xlsx", headers=admin_headers)
            assert resp.status_code == 404
            assert "not found on disk" in resp.json()["detail"]
        finally:
            base_mod.SAMPLES_DIR = original
