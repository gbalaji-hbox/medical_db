"""
Input file validation: extension, size, and magic-byte checks.
Raises HTTP 400/413 on invalid input; returns raw bytes on success.
"""

from pathlib import Path

from fastapi import HTTPException, UploadFile

from src.api.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES

# First-bytes signatures for supported formats
_MAGIC: dict[str, bytes] = {
    ".xlsx": b"PK\x03\x04",         # ZIP / Office Open XML
    ".xls": b"\xd0\xcf\x11\xe0",    # OLE2 Compound Document
    ".csv": b"",                     # No fixed magic; validated by encoding
}


async def validate_upload(file: UploadFile, label: str = "file") -> bytes:
    """
    Read the upload into memory, run all validation checks, reset stream.
    Returns raw bytes so callers can write to disk without re-reading.
    """
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{label}: extension '{ext}' not allowed. "
                f"Accepted: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(status_code=400, detail=f"{label}: uploaded file is empty")

    if len(content) > MAX_UPLOAD_BYTES:
        mb = MAX_UPLOAD_BYTES // (1024 * 1024)
        raise HTTPException(status_code=413, detail=f"{label}: file exceeds {mb} MB limit")

    magic = _MAGIC.get(ext, b"")
    if magic and not content.startswith(magic):
        raise HTTPException(
            status_code=400,
            detail=f"{label}: file content does not match expected format for {ext}",
        )

    if ext == ".csv":
        _validate_csv_encoding(content, label)

    await file.seek(0)
    return content


def _validate_csv_encoding(content: bytes, label: str) -> None:
    """
    Reject obvious binary content in CSV uploads.
    Null bytes are reliable indicators of binary files (executables, zips, etc.).
    After that, accept UTF-8 or latin-1 encoded text.
    """
    sample = content[:512]
    if b"\x00" in sample:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: CSV file appears to be binary (null bytes detected)",
        )
    try:
        sample.decode("utf-8")
        return
    except UnicodeDecodeError:
        pass
    try:
        sample.decode("latin-1")
        return
    except UnicodeDecodeError:
        pass
    raise HTTPException(
        status_code=400,
        detail=f"{label}: CSV file does not appear to be valid text",
    )
