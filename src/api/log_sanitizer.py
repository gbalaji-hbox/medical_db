"""
Strip PHI-bearing content from pipeline stdout before storing in the DB.

Strategy: allowlist safe line patterns; replace everything else with a
placeholder. Also redact high-risk token patterns inside safe lines.
"""

import re

_SAFE_RE = re.compile(
    r"^("
    r"=+.*=+|"              # === headers ===
    r"Step \d+:|"           # Step N:
    r"OK:|"                 # OK: message
    r"ERROR:|"              # ERROR: message
    r"WARNING:|"            # WARNING: message
    r"Cleanup:|"            # Cleanup: message
    r"Total patients:|"
    r"Final template:|"
    r"Raw consolidated|"
    r"Processing (complete|failed)|"
    r"[A-Za-z ]+file:? \d+|"  # "Insurance file: 11681"
    r"[A-Za-z ]+: \d+ records|"  # "... 3433 records"
    r"[A-Za-z ]+merged: \d+|"
    r"[A-Za-z ]+cleaned: \d+|"
    r"[A-Za-z ]+combined: \d+|"
    r"\s*$"                  # blank
    r")",
    re.IGNORECASE,
)

# High-risk patterns redacted even inside safe lines
_PHI_RE = [
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                          # SSN
    re.compile(r"\b[A-Z][a-z]+,\s+[A-Z][a-z]+\b"),                 # Last, First name
    re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),  # email
    re.compile(r"\(\d{3}\)\s*\d{3}[-\s]\d{4}"),                    # phone (XXX) XXX-XXXX
]


def sanitize_log(raw_log: str, max_chars: int = 8000) -> str:
    """Return a PHI-scrubbed version of raw subprocess output."""
    lines = raw_log.splitlines()
    out: list[str] = []

    for line in lines:
        if not _SAFE_RE.match(line):
            out.append("[log line redacted]")
            continue
        for phi in _PHI_RE:
            line = phi.sub("[REDACTED]", line)
        out.append(line)

    result = "\n".join(out)
    return result[-max_chars:] if len(result) > max_chars else result
