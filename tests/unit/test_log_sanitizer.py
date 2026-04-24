"""Unit tests for PHI log sanitization."""

import pytest

from src.api.log_sanitizer import sanitize_log


class TestSafeLines:
    def test_step_header_passes(self):
        result = sanitize_log("Step 1: Loading files")
        assert "Step 1: Loading files" in result
        assert "[log line redacted]" not in result

    def test_ok_line_passes(self):
        result = sanitize_log("OK: Insurance file loaded")
        assert "OK:" in result

    def test_error_line_passes(self):
        result = sanitize_log("ERROR: File not found")
        assert "ERROR:" in result

    def test_warning_line_passes(self):
        result = sanitize_log("WARNING: Missing column")
        assert "WARNING:" in result

    def test_blank_line_passes(self):
        result = sanitize_log("\n\n")
        assert "[log line redacted]" not in result

    def test_section_header_passes(self):
        result = sanitize_log("=== Processing Complete ===")
        assert "===" in result

    def test_record_count_passes(self):
        result = sanitize_log("Insurance file: 1234")
        assert "1234" in result


class TestUnsafeLines:
    def test_patient_name_line_redacted(self):
        result = sanitize_log("Loading patient: Smith, John")
        assert "Smith, John" not in result
        assert "[log line redacted]" in result

    def test_arbitrary_data_line_redacted(self):
        result = sanitize_log("patient_id=12345 dob=1990-01-01 mrn=A9876")
        assert "patient_id" not in result
        assert "[log line redacted]" in result

    def test_stack_trace_redacted(self):
        result = sanitize_log('File "main.py", line 42, in process_data')
        assert "main.py" not in result
        assert "[log line redacted]" in result


class TestPhiRedactionInSafeLines:
    def test_ssn_redacted(self):
        result = sanitize_log("OK: processed 123-45-6789")
        assert "123-45-6789" not in result
        assert "[REDACTED]" in result

    def test_email_redacted(self):
        result = sanitize_log("OK: sent to patient@example.com")
        assert "patient@example.com" not in result
        assert "[REDACTED]" in result

    def test_phone_redacted(self):
        result = sanitize_log("OK: called (555) 123-4567")
        assert "(555) 123-4567" not in result
        assert "[REDACTED]" in result

    def test_name_pattern_redacted(self):
        result = sanitize_log("OK: processed Doe, Jane")
        assert "Doe, Jane" not in result
        assert "[REDACTED]" in result


class TestMaxChars:
    def test_output_truncated_to_max_chars(self):
        long_log = ("OK: step\n" * 2000)
        result = sanitize_log(long_log, max_chars=100)
        assert len(result) <= 100

    def test_short_log_not_truncated(self):
        short = "OK: done"
        result = sanitize_log(short, max_chars=8000)
        assert result == short

    def test_empty_log(self):
        assert sanitize_log("") == ""


class TestMixedLog:
    def test_safe_and_unsafe_lines_mixed(self):
        log = "\n".join([
            "Step 1: Starting",
            "patient_name=John Doe",  # unsafe
            "OK: 500 records loaded",
            "SELECT * FROM patients",  # unsafe
            "Processing complete",
        ])
        result = sanitize_log(log)
        assert "Step 1: Starting" in result
        assert "OK: 500 records loaded" in result
        assert "patient_name=John Doe" not in result
        assert "SELECT * FROM patients" not in result
        assert result.count("[log line redacted]") == 2
