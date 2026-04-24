"""
Input file validation: extension, size, and magic-byte checks.
"""

from fastapi import HTTPException, UploadFile

from src.api.config import ALLOWED_EXTENSIONS, MAX_UPLOAD_BYTES

# First-bytes signatures for supported formats
_MAGIC: dict[str, bytes] = {
    ".xlsx": b"PK\x03\x04",               # ZIP (Office Open XML)
    ".xls": b"\xd0\xcf\x11\xe0",          # OLE2 Compound Document
    ".csv": b"",                           # No fixed magic; validated by content
}

_XLSX_MAX = 4
_XLS_MAX = 4


async def validate_upload(file: UploadFile, label: str = "file") -> bytes:
    """
    Read the upload into memory, validate it, reset position.
    Returns the raw bytes so callers can write without re-reading.
    Raises HTTP 400/413 on invalid input.
    """
    from pathlib import Path

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"{label}: extension '{ext}' not allowed. Accepted: {sorted(ALLOWED_EXTENSIONS)}",
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

    # For CSV: ensure first 512 bytes are decodable as UTF-8 or latin-1
    if ext == ".csv":
        try:
            content[:512].decode("utf-8")
        except UnicodeDecodeError:
            try:
                content[:512].decode("latin-1")
            except UnicodeDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail=f"{label}: CSV file does not appear to be text",
                )

    await file.seek(0)
    return content
