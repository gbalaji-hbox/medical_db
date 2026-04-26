"""Unit tests for GET /api/scripts/* endpoints."""


class TestScriptsEndpoints:
    def test_get_ts_script_requires_auth(self, client):
        assert client.get("/api/scripts/drchrono-submit.ts").status_code == 401

    def test_get_bat_requires_auth(self, client):
        assert client.get("/api/scripts/run_drchrono.bat").status_code == 401

    def test_get_ts_script_returns_text(self, client, admin_headers):
        resp = client.get("/api/scripts/drchrono-submit.ts", headers=admin_headers)
        assert resp.status_code == 200
        assert "drchrono-submit" in resp.text
        assert "workflow" in resp.text

    def test_get_bat_returns_file(self, client, admin_headers):
        resp = client.get("/api/scripts/run_drchrono.bat", headers=admin_headers)
        assert resp.status_code == 200
        assert resp.headers["content-disposition"] == 'attachment; filename="run_drchrono.bat"'
        assert b"npx" in resp.content
        assert b"libretto" in resp.content

    def test_get_ts_script_with_api_key(self, client, admin_headers):
        # Create an API key and verify the endpoint also accepts X-Api-Key auth
        key_resp = client.post(
            "/api/auth/keys",
            json={"name": "scripts-test-key"},
            headers=admin_headers,
        )
        assert key_resp.status_code == 200
        api_key = key_resp.json()["key"]

        resp = client.get(
            "/api/scripts/drchrono-submit.ts",
            headers={"X-Api-Key": api_key},
        )
        assert resp.status_code == 200
