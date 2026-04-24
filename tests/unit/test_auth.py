"""Unit tests for authentication helpers and auth endpoints."""

import time

import pytest

from src.api.auth import (
    _decode_token,
    _hash_api_key,
    _hash_password,
    _make_token,
    _verify_password,
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_hash_creates_bcrypt_format(self):
        assert _hash_password("secret").startswith("$2b$")

    def test_verify_correct_password(self):
        h = _hash_password("correct-horse")
        assert _verify_password("correct-horse", h) is True

    def test_verify_wrong_password(self):
        h = _hash_password("correct-horse")
        assert _verify_password("battery-staple", h) is False

    def test_verify_empty_password(self):
        h = _hash_password("nonempty")
        assert _verify_password("", h) is False

    def test_hashes_are_unique_per_call(self):
        # bcrypt uses a random salt — same plaintext → different hashes
        h1 = _hash_password("same")
        h2 = _hash_password("same")
        assert h1 != h2
        # But both must verify correctly
        assert _verify_password("same", h1) is True
        assert _verify_password("same", h2) is True


# ---------------------------------------------------------------------------
# API key hashing
# ---------------------------------------------------------------------------

class TestApiKeyHashing:
    def test_deterministic(self):
        assert _hash_api_key("my-key") == _hash_api_key("my-key")

    def test_sha256_length(self):
        assert len(_hash_api_key("anything")) == 64

    def test_different_keys_differ(self):
        assert _hash_api_key("key-a") != _hash_api_key("key-b")

    def test_empty_key(self):
        result = _hash_api_key("")
        assert len(result) == 64  # still returns a valid SHA-256


# ---------------------------------------------------------------------------
# JWT tokens
# ---------------------------------------------------------------------------

class TestJwt:
    def test_encode_decode_roundtrip(self):
        token = _make_token({"sub": "alice", "type": "access"}, 300)
        payload = _decode_token(token)
        assert payload is not None
        assert payload["sub"] == "alice"
        assert payload["type"] == "access"

    def test_token_has_iat_and_exp(self):
        before = time.time()
        token = _make_token({"sub": "alice"}, 300)
        payload = _decode_token(token)
        assert payload["iat"] >= before
        assert payload["exp"] > payload["iat"]

    def test_expired_token_returns_none(self):
        token = _make_token({"sub": "alice"}, -1)
        assert _decode_token(token) is None

    def test_invalid_string_returns_none(self):
        assert _decode_token("not.a.jwt") is None

    def test_empty_string_returns_none(self):
        assert _decode_token("") is None

    def test_tampered_token_returns_none(self):
        token = _make_token({"sub": "alice"}, 300)
        tampered = token[:-4] + "XXXX"
        assert _decode_token(tampered) is None


# ---------------------------------------------------------------------------
# Auth endpoints via TestClient
# ---------------------------------------------------------------------------

class TestLoginEndpoint:
    def test_login_success(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "HBox@123456!"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_wrong_password(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/api/auth/login", json={"username": "nobody", "password": "pass"})
        assert resp.status_code == 401

    def test_login_missing_password_field(self, client):
        resp = client.post("/api/auth/login", json={"username": "admin"})
        assert resp.status_code == 422

    def test_login_empty_username(self, client):
        resp = client.post("/api/auth/login", json={"username": "", "password": "HBox@123456!"})
        assert resp.status_code == 422


class TestRefreshEndpoint:
    def test_refresh_returns_new_access_token(self, client):
        login = client.post("/api/auth/login", json={"username": "admin", "password": "HBox@123456!"})
        refresh_token = login.json()["refresh_token"]
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_with_access_token_fails(self, client, admin_token):
        resp = client.post("/api/auth/refresh", json={"refresh_token": admin_token})
        assert resp.status_code == 401

    def test_refresh_with_garbage_fails(self, client):
        resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-token"})
        assert resp.status_code == 401


class TestProtectedEndpoints:
    def test_no_credentials_returns_401(self, client):
        resp = client.get("/api/cam/jobs/fake-id")
        assert resp.status_code == 401

    def test_invalid_bearer_returns_401(self, client):
        resp = client.get("/api/cam/jobs/fake-id", headers={"Authorization": "Bearer garbage"})
        assert resp.status_code == 401

    def test_valid_jwt_grants_access(self, client, admin_headers):
        resp = client.get("/api/jobs", headers=admin_headers)
        assert resp.status_code == 200

    def test_valid_api_key_grants_access(self, client, admin_headers):
        # Create an API key then use it
        create = client.post(
            "/api/auth/keys",
            json={"name": "test-key", "role": "user"},
            headers=admin_headers,
        )
        assert create.status_code == 200
        raw_key = create.json()["key"]

        resp = client.get("/api/jobs", headers={"X-Api-Key": raw_key})
        assert resp.status_code == 200


class TestApiKeyManagement:
    def test_non_admin_cannot_create_key(self, client):
        # No token at all → 401
        resp = client.post("/api/auth/keys", json={"name": "k", "role": "user"})
        assert resp.status_code == 401

    def test_create_and_list_key(self, client, admin_headers):
        create = client.post(
            "/api/auth/keys",
            json={"name": "listing-test-key", "role": "user"},
            headers=admin_headers,
        )
        assert create.status_code == 200
        key_id = create.json()["key_id"]

        listing = client.get("/api/auth/keys", headers=admin_headers)
        assert listing.status_code == 200
        ids = [k["key_id"] for k in listing.json()]
        assert key_id in ids

    def test_revoke_key(self, client, admin_headers):
        create = client.post(
            "/api/auth/keys",
            json={"name": "revoke-me", "role": "user"},
            headers=admin_headers,
        )
        key_id = create.json()["key_id"]
        raw_key = create.json()["key"]

        # Key works before revocation
        assert client.get("/api/jobs", headers={"X-Api-Key": raw_key}).status_code == 200

        # Revoke
        rev = client.delete(f"/api/auth/keys/{key_id}", headers=admin_headers)
        assert rev.status_code == 200

        # Key no longer works
        assert client.get("/api/jobs", headers={"X-Api-Key": raw_key}).status_code == 401

    def test_revoke_nonexistent_key(self, client, admin_headers):
        resp = client.delete("/api/auth/keys/00000000-0000-0000-0000-000000000000", headers=admin_headers)
        assert resp.status_code == 404
