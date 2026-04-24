"""Unit tests for file upload validation."""

import pytest

from src.api.validators import validate_upload

# Magic bytes for supported formats
_XLSX_MAGIC = b"PK\x03\x04" + b"\x00" * 97       # ZIP header
_XLS_MAGIC = b"\xd0\xcf\x11\xe0" + b"\x00" * 96  # OLE2 header
_CSV_CONTENT = b"patient_id,name,dob\n1,John,2000-01-01\n"


class MockUploadFile:
    """Minimal UploadFile stand-in for unit testing."""

    def __init__(self, content: bytes, filename: str):
        self.filename = filename
        self._content = content
        self._pos = 0

    async def read(self) -> bytes:
        return self._content

    async def seek(self, pos: int) -> None:
        self._pos = pos


# ---------------------------------------------------------------------------
# Extension checks
# ---------------------------------------------------------------------------

class TestExtensionValidation:
    @pytest.mark.asyncio
    async def test_xlsx_accepted(self):
        f = MockUploadFile(_XLSX_MAGIC, "report.xlsx")
        result = await validate_upload(f, "report")
        assert result == _XLSX_MAGIC

    @pytest.mark.asyncio
    async def test_xls_accepted(self):
        f = MockUploadFile(_XLS_MAGIC, "report.xls")
        result = await validate_upload(f, "report")
        assert result == _XLS_MAGIC

    @pytest.mark.asyncio
    async def test_csv_accepted(self):
        f = MockUploadFile(_CSV_CONTENT, "data.csv")
        result = await validate_upload(f, "data")
        assert result == _CSV_CONTENT

    @pytest.mark.asyncio
    async def test_pdf_rejected(self):
        f = MockUploadFile(b"%PDF-1.4 content", "report.pdf")
        with pytest.raises(Exception) as exc:
            await validate_upload(f, "report")
        assert exc.value.status_code == 400
        assert "not allowed" in exc.value.detail

    @pytest.mark.asyncio
    async def test_no_extension_rejected(self):
        f = MockUploadFile(_XLSX_MAGIC, "noextension")
        with pytest.raises(Exception) as exc:
            await validate_upload(f, "file")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_case_insensitive_extension(self):
        f = MockUploadFile(_XLSX_MAGIC, "REPORT.XLSX")
        result = await validate_upload(f, "report")
        assert result == _XLSX_MAGIC


# ---------------------------------------------------------------------------
# Size checks
# ---------------------------------------------------------------------------

class TestSizeValidation:
    @pytest.mark.asyncio
    async def test_empty_file_rejected(self):
        f = MockUploadFile(b"", "empty.xlsx")
        with pytest.raises(Exception) as exc:
            await validate_upload(f, "file")
        assert exc.value.status_code == 400
        assert "empty" in exc.value.detail

    @pytest.mark.asyncio
    async def test_oversized_file_rejected(self):
        big = b"PK\x03\x04" + b"A" * (51 * 1024 * 1024)  # 51 MB
        f = MockUploadFile(big, "big.xlsx")
        with pytest.raises(Exception) as exc:
            await validate_upload(f, "file")
        assert exc.value.status_code == 413
        assert "50 MB" in exc.value.detail


# ---------------------------------------------------------------------------
# Magic byte checks
# ---------------------------------------------------------------------------

class TestMagicByteValidation:
    @pytest.mark.asyncio
    async def test_xlsx_with_wrong_magic_rejected(self):
        f = MockUploadFile(b"not a zip file at all", "fake.xlsx")
        with pytest.raises(Exception) as exc:
            await validate_upload(f, "file")
        assert exc.value.status_code == 400
        assert ".xlsx" in exc.value.detail

    @pytest.mark.asyncio
    async def test_xls_with_wrong_magic_rejected(self):
        f = MockUploadFile(b"PK wrong magic", "fake.xls")
        with pytest.raises(Exception) as exc:
            await validate_upload(f, "file")
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_csv_has_no_magic_requirement(self):
        # Any text content is valid for CSV
        f = MockUploadFile(b"col1,col2\nval1,val2", "data.csv")
        result = await validate_upload(f, "data")
        assert len(result) > 0


# ---------------------------------------------------------------------------
# CSV encoding checks
# ---------------------------------------------------------------------------

class TestCsvEncoding:
    @pytest.mark.asyncio
    async def test_utf8_csv_accepted(self):
        content = "id,name\n1,José\n".encode("utf-8")
        f = MockUploadFile(content, "data.csv")
        result = await validate_upload(f, "data")
        assert result == content

    @pytest.mark.asyncio
    async def test_latin1_csv_accepted(self):
        content = "id,name\n1,caf\xe9\n"  # café in latin-1
        f = MockUploadFile(content.encode("latin-1"), "data.csv")
        result = await validate_upload(f, "data")
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_binary_csv_rejected(self):
        # Null bytes are a reliable binary indicator (e.g. executables, zip headers)
        f = MockUploadFile(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\xff\xff\x00\x00", "data.csv")
        with pytest.raises(Exception) as exc:
            await validate_upload(f, "data")
        assert exc.value.status_code == 400
        assert "binary" in exc.value.detail
