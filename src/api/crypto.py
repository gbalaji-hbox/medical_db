"""
Fernet (AES-128-CBC + HMAC-SHA256) encryption for pipeline output files.

Key lifecycle:
  1. On first startup: generate a new Fernet key, write it to KEY_FILE (chmod 600).
  2. On subsequent startups: load the key from KEY_FILE.
  3. ENCRYPTION_KEY_FILE env var overrides the key file path.

The key file lives on the same Docker volume as the SQLite DB so it survives
container restarts without any manual secret management.
"""

import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet

from src.api.config import KEY_FILE

logger = logging.getLogger(__name__)


def _load_or_create_key(key_file: Path) -> Fernet:
    if key_file.exists():
        key = key_file.read_bytes().strip()
        logger.info("Encryption key loaded from %s", key_file)
    else:
        key = Fernet.generate_key()
        key_file.parent.mkdir(parents=True, exist_ok=True)
        key_file.write_bytes(key)
        try:
            os.chmod(key_file, 0o600)  # owner read/write only; no-op on Windows
        except Exception:
            pass
        logger.info("Encryption key generated and saved to %s", key_file)
    return Fernet(key)


_FERNET: Fernet = _load_or_create_key(KEY_FILE)


def encrypt_file(path: Path) -> Path:
    """Encrypt a plaintext output file in-place. Returns the .enc path."""
    plaintext = path.read_bytes()
    enc_path = path.with_suffix(path.suffix + ".enc")
    enc_path.write_bytes(_FERNET.encrypt(plaintext))
    path.unlink()
    return enc_path


def decrypt_to_bytes(path: Path) -> bytes:
    """Decrypt an encrypted output file and return raw bytes for streaming."""
    return _FERNET.decrypt(path.read_bytes())
