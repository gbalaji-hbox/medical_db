"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError

from src.api.models import (
    ApiKeyCreated,
    ApiKeyInfo,
    ApiKeyRequest,
    JobCreated,
    JobStatus,
    LoginRequest,
    RefreshRequest,
    Token,
)


class TestLoginRequest:
    def test_valid(self):
        m = LoginRequest(username="admin", password="secret")
        assert m.username == "admin"
        assert m.password == "secret"

    def test_empty_username_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="", password="secret")

    def test_empty_password_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="admin", password="")

    def test_missing_fields_rejected(self):
        with pytest.raises(ValidationError):
            LoginRequest(username="admin")


class TestRefreshRequest:
    def test_valid(self):
        m = RefreshRequest(refresh_token="some.token.here")
        assert m.refresh_token == "some.token.here"


class TestJobStatus:
    def test_minimal_valid(self):
        m = JobStatus(
            job_id="abc-123",
            module="cam",
            status="queued",
            created_at=1_700_000_000.0,
        )
        assert m.log == ""
        assert m.started_at is None
        assert m.output_file is None

    def test_full_valid(self):
        m = JobStatus(
            job_id="abc",
            module="mca",
            status="done",
            created_at=1.0,
            started_at=2.0,
            finished_at=3.0,
            returncode=0,
            log="OK: done",
            output_file="/tmp/out.xlsx.enc",
            submitted_by="admin",
        )
        assert m.returncode == 0
        assert m.submitted_by == "admin"


class TestJobCreated:
    def test_valid(self):
        m = JobCreated(job_id="x", module="hct", status="queued", message="queued")
        assert m.module == "hct"


class TestApiKeyInfo:
    def test_is_active_accepts_bool(self):
        m = ApiKeyInfo(
            key_id="k1",
            name="mykey",
            created_by="admin",
            created_at=1.0,
            is_active=True,
            role="user",
        )
        assert m.is_active is True

    def test_is_active_coerces_int_one(self):
        m = ApiKeyInfo(
            key_id="k2",
            name="n",
            created_by="a",
            created_at=1.0,
            is_active=1,
            role="user",
        )
        assert m.is_active is True

    def test_is_active_coerces_int_zero(self):
        m = ApiKeyInfo(
            key_id="k3",
            name="n",
            created_by="a",
            created_at=1.0,
            is_active=0,
            role="user",
        )
        assert m.is_active is False

    def test_last_used_at_optional(self):
        m = ApiKeyInfo(
            key_id="k4", name="n", created_by="a", created_at=1.0, is_active=True, role="user"
        )
        assert m.last_used_at is None


class TestApiKeyRequest:
    def test_default_role_is_user(self):
        m = ApiKeyRequest(name="my-key")
        assert m.role == "user"

    def test_empty_name_rejected(self):
        with pytest.raises(ValidationError):
            ApiKeyRequest(name="")


class TestToken:
    def test_default_token_type(self):
        m = Token(
            access_token="a", refresh_token="r", expires_in=1800
        )
        assert m.token_type == "bearer"
