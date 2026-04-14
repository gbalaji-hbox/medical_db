# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **medical data ETL pipeline** that consolidates patient records from multiple healthcare systems (EMR exports) into unified, cleaned Excel datasets. Each module handles a different data source with the same structural pattern.

## Running Pipelines

Always run scripts from the **project root**, not from within the module directory:

```bash
# Activate virtual environment first
.venv/Scripts/activate          # Windows
source .venv/bin/activate       # Linux/Mac

# Run a specific module pipeline
python src/MCA/scripts/main.py
python src/HCT/scripts/main.py
python src/SSC/scripts/main.py
python src/CAM/scripts/main.py
python src/CIM/scripts/main.py
python src/XHI/scripts/main.py
```

Install dependencies:
```bash
pip install -r requirements.txt
```

There are no automated tests, linter configs, or build steps.

## Architecture

Six parallel processing modules, each following the same pattern:

```
src/{MODULE}/
├── scripts/
│   ├── main.py                     # Orchestrator — run this
│   ├── data_cleaner.py             # Cleaner classes per data source
│   ├── merger.py                   # Merge logic with conflict resolution
│   └── convert_to_consolidate.py   # Maps cleaned data to output template
├── template/                       # consolidated_view-template - new.xlsx (reference)
├── cleaned/                        # Intermediate CSVs (timestamped, git-ignored)
└── output/                         # Final {MODULE}_consolidated_{timestamp}.xlsx
```

**Data flow:** Input Excel/XLS files → cleaners → intermediate CSVs in `cleaned/` → mergers → template formatter → `output/{MODULE}_consolidated_YYYYMMDD_HHMMSS.xlsx`

Input files (placed in the module root, e.g. `src/MCA/`) are git-ignored because they contain patient data. The `.xls` → `.xlsx` conversion happens automatically at runtime via Spire.XLS.

## Module Purposes

| Module | Description |
|--------|-------------|
| MCA | Main patient consolidation: insurance, visits, demographics, copay |
| HCT | Demographics + ICD code grouping, insurance |
| SSC | Chronic care management: medications + diagnoses |
| CAM | Registry/problem list comorbidity mapping, provider parsing |
| CIM | Intensive care management (similar structure to CAM) |
| XHI | External EMR final report: medications + problem mapping |

## Key Conventions

**Data merging priority** (highest wins): insurance data > visits data > patient list data. Emergency contact always comes from the patient list "Notes Er contact" field.

**Text cleaning** removes Excel artifacts (`_x000D_`, `_x000A_`), normalizes phone numbers to `(XXX) XXX-XXXX`, and strips whitespace. These cleaners are in `data_cleaner.py` for each module.

**Column/field mapping** for the consolidated output template lives in `convert_to_consolidate.py`. When adding new source fields, add mapping logic there.

**ICD-10 codes** used throughout (e.g. `I10` = Hypertension, `E11` = Type 2 Diabetes, `I50` = CHF). See `src/MCA/README.md` for the full mapping table with suggested vitals.

## Data Source (EMR)

Reports are extracted manually from **CGM APRIMA** via RDP. Extraction SOPs with navigation paths are documented in `src/MCA/README.md` and `src/MCA/README_reports.md`. Credentials are stored in `.creds/` (git-ignored).

## Troubleshooting

- **Permission denied on CSV files**: Close the file in Excel before re-running.
- **Import errors**: Ensure you're running from the project root, not from inside `scripts/`.
- **Missing input files**: Place the Excel exports in the module root directory (e.g. `src/MCA/`) before running.
