"""
Output file retention and input file cleanup.

Retention: keeps the N most-recently-modified output files per module;
deletes the rest. Called after every successful pipeline run.

Cleanup: deletes raw input data files from the module input directory
after a successful run. Template files (api_prescriptioncauselist_*.csv,
consolidated_view-template*.xlsx) are never touched.
"""

import logging
from pathlib import Path

from src.api.config import (
    MODULE_INPUT_DIR,
    MODULE_INPUT_FILES,
    MODULE_OUTPUT_DIR,
    OUTPUT_GLOB,
    OUTPUT_RETENTION_COUNT,
)

log = logging.getLogger(__name__)


def enforce_output_retention(module: str, max_files: int = OUTPUT_RETENTION_COUNT) -> None:
    """Delete output files beyond the retention limit (oldest first)."""
    output_dir = MODULE_OUTPUT_DIR[module]
    pattern = OUTPUT_GLOB[module]
    files = sorted(output_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[max_files:]:
        try:
            old.unlink()
            log.info("Retention: deleted old output %s", old.name)
        except OSError as exc:
            log.warning("Retention: could not delete %s: %s", old.name, exc)


def cleanup_inputs(module: str) -> None:
    """
    Delete uploaded input data files after a successful pipeline run.
    Only touches files listed in MODULE_INPUT_FILES; never deletes templates.
    """
    input_dir: Path = MODULE_INPUT_DIR[module]
    for filename in MODULE_INPUT_FILES.get(module, []):
        path = input_dir / filename
        if path.exists():
            try:
                path.unlink()
                log.info("Cleanup: deleted input file %s", filename)
            except OSError as exc:
                log.warning("Cleanup: could not delete %s: %s", filename, exc)
