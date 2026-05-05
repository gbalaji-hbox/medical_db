"""
HCN Drugs PDF → raw CSV extractor.

Streams DrugsByDiagnosis PDF page by page and writes one row per page to
src/HCN/cleaned/drugs_raw_<timestamp>.csv.
"""

import csv
import sys
from datetime import datetime
from pathlib import Path

import fitz  # PyMuPDF

MODULE_DIR = Path(__file__).resolve().parents[1]
CLEANED_DIR = MODULE_DIR / "cleaned"
CLEANED_DIR.mkdir(exist_ok=True)

DRUGS_PDF = next(
    (f for f in sorted(MODULE_DIR.glob("Drugs*.PDF"))),
    next((f for f in sorted(MODULE_DIR.glob("Drugs*.pdf"))), None),
)


def extract(pdf_path: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = CLEANED_DIR / f"drugs_raw_{ts}.csv"

    doc = fitz.open(str(pdf_path))
    total = doc.page_count

    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["page_num", "raw_text"])
        for i in range(total):
            text = doc[i].get_text()
            writer.writerow([i + 1, text.replace("\n", "\\n")])
            if (i + 1) % 20 == 0:
                print(f"  extracted {i+1}/{total} pages", flush=True)

    doc.close()
    print(f"Raw CSV written: {out_csv}  ({total} pages)")
    return out_csv


if __name__ == "__main__":
    if DRUGS_PDF is None:
        print("ERROR: No Drugs*.PDF found in", MODULE_DIR)
        sys.exit(1)
    print(f"PDF: {DRUGS_PDF.name}")
    extract(DRUGS_PDF)
