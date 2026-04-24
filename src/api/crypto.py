"""
Lightweight symmetric encryption for output files at rest.

Algorithm: Fernet (AES-128-CBC + HMAC-SHA256) from the `cryptography` package.
Key: 32-byte URL-safe base64 string stored in ENCRYPTION_KEY env var.

If ENCRYPTION_KEY is not set, functions are no-ops (plaintext storage).
This lets development work without key management while enforcing encryption
in production by requiring the env var in the Docker/server environment.

Generate a key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import io
from pathlib import Path
from typing import Optional

from src.api.config import ENCRYPTION_KEY


def _fernet():
    """Return a Fernet instance or None if no key configured."""
    if not ENCRYPTION_KEY:
        return None
    from cryptography.fernet import Fernet

    return Fernet(
        ENCRYPTION_KEY.encode() if isinstance(ENCRYPTION_KEY, str) else ENCRYPTION_KEY
    )


def encrypt_file(path: Path) -> Path:
    """
    Encrypt a file in-place. Returns the new .enc path.
    If no key is configured, returns the original path unchanged.
    """
    f = _fernet()
    if f is None:
        return path

    plaintext = path.read_bytes()
    ciphertext = f.encrypt(plaintext)

    enc_path = path.with_suffix(path.suffix + ".enc")
    enc_path.write_bytes(ciphertext)
    path.unlink()
    return enc_path


def decrypt_to_bytes(path: Path) -> bytes:
    """
    Read a file (encrypted or plaintext) and return decrypted bytes.
    If no key is configured, reads the file as-is.
    """
    f = _fernet()
    raw = path.read_bytes()
    if f is None:
        return raw
    return f.decrypt(raw)


def is_encrypted(path: Path) -> bool:
    return path.suffix == ".enc"
