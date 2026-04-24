"""Unit tests for Fernet encryption helpers."""

import tempfile
from pathlib import Path

import pytest
from cryptography.fernet import Fernet


def _make_fernet_env(tmp_path: Path):
    """Return a fresh Fernet instance backed by a key in tmp_path."""
    key_file = tmp_path / "enc.key"
    from src.api.crypto import _load_or_create_key
    return _load_or_create_key(key_file), key_file


class TestKeyLifecycle:
    def test_key_file_created_on_first_call(self, tmp_path):
        key_file = tmp_path / "enc.key"
        assert not key_file.exists()
        from src.api.crypto import _load_or_create_key
        _load_or_create_key(key_file)
        assert key_file.exists()

    def test_key_file_contains_valid_fernet_key(self, tmp_path):
        key_file = tmp_path / "enc.key"
        from src.api.crypto import _load_or_create_key
        _load_or_create_key(key_file)
        key_bytes = key_file.read_bytes().strip()
        # Must not raise — Fernet validates key format
        Fernet(key_bytes)

    def test_same_key_reloaded_on_second_call(self, tmp_path):
        key_file = tmp_path / "enc.key"
        from src.api.crypto import _load_or_create_key
        f1 = _load_or_create_key(key_file)
        f2 = _load_or_create_key(key_file)
        # Both instances encrypt with the same key — cross-decrypt must work
        ct = f1.encrypt(b"hello")
        assert f2.decrypt(ct) == b"hello"

    def test_different_paths_produce_different_keys(self, tmp_path):
        from src.api.crypto import _load_or_create_key
        f1 = _load_or_create_key(tmp_path / "key1.key")
        f2 = _load_or_create_key(tmp_path / "key2.key")
        ct = f1.encrypt(b"data")
        with pytest.raises(Exception):
            f2.decrypt(ct)


class TestEncryptDecrypt:
    def test_encrypt_removes_plaintext(self, tmp_path):
        f, _ = _make_fernet_env(tmp_path)
        plain = tmp_path / "output.xlsx"
        plain.write_bytes(b"fake xlsx content")

        from src.api.crypto import encrypt_file
        import importlib, sys
        # Patch the module-level _FERNET with our test instance
        import src.api.crypto as crypto_mod
        original = crypto_mod._FERNET
        crypto_mod._FERNET = f
        try:
            enc = encrypt_file(plain)
            assert not plain.exists()
            assert enc.suffix == ".enc"
            assert enc.exists()
        finally:
            crypto_mod._FERNET = original

    def test_decrypt_returns_original_bytes(self, tmp_path):
        f, _ = _make_fernet_env(tmp_path)
        original_data = b"patient data xlsx bytes"

        import src.api.crypto as crypto_mod
        saved = crypto_mod._FERNET
        crypto_mod._FERNET = f
        try:
            plain = tmp_path / "output.xlsx"
            plain.write_bytes(original_data)
            enc = crypto_mod.encrypt_file(plain)
            result = crypto_mod.decrypt_to_bytes(enc)
            assert result == original_data
        finally:
            crypto_mod._FERNET = saved

    def test_encrypt_file_name_has_enc_suffix(self, tmp_path):
        f, _ = _make_fernet_env(tmp_path)
        import src.api.crypto as crypto_mod
        saved = crypto_mod._FERNET
        crypto_mod._FERNET = f
        try:
            p = tmp_path / "CAM_consolidated_20260101_120000.xlsx"
            p.write_bytes(b"data")
            enc = crypto_mod.encrypt_file(p)
            assert enc.name == "CAM_consolidated_20260101_120000.xlsx.enc"
        finally:
            crypto_mod._FERNET = saved

    def test_removesuffix_gives_original_name(self, tmp_path):
        enc_name = "CAM_consolidated_20260101_120000.xlsx.enc"
        result = enc_name.removesuffix(".enc")
        assert result == "CAM_consolidated_20260101_120000.xlsx"
