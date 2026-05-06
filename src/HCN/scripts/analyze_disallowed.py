"""
Analyze the ~31K HCN patients whose only resolved comorbidities are disallowed
as PRIMARY DX (ANGINA PECTORIS, DIABETES, OBESITY, etc.).

For each such patient we collect:
  - All raw ICD codes from DetailedDiagnosisAnalysis PDF (not just mapped ones)
  - All medications from PatientMedication PDF
  - Encounter note text from PatientReport PDF

Then we print:
  1. Top raw ICD codes + descriptions
  2. ICD codes that MAP to comorbidities (i.e. heart conditions we ARE tracking)
  3. ICD codes that DON'T map (potential coverage gaps)
  4. Top medications
  5. Most common note keywords

Usage:
    python src/HCN/scripts/analyze_disallowed.py
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime

# Reuse all parsers and mappings from main.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import (
    MODULE_DIR, CLEANED_DIR, OUTPUT_DIR,
    PDF_PATH, DRUGS_PDF_PATH, DIAG_PDF_PATH,
    parse_page, parse_drugs_csv, parse_diag_csv,
    extract_drugs_to_csv, extract_diag_to_csv,
    _load_api_mappings, _match_icd, _desc_comorbidity,
    _pick_primary_secondary, _COMORBIDITY_COLUMNS,
    _PRIMARY_DX_DISALLOWED, API_CAUSE_CSV,
    _infer_comorb_from_drug,
)
import fitz

CLEANED_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Step 1 — Scan PatientReport PDF: collect disallowed-primary patient IDs
#           and their encounter notes
# ---------------------------------------------------------------------------

def scan_patient_report(exact_icd, prefix_icd):
    """
    Returns:
      disallowed_pids : set of EMR IDs whose resolved primary DX is disallowed
      notes_by_pid    : dict emr_id -> list[str] of note lines
    """
    print(f"Scanning PatientReport PDF ({PDF_PATH.name}) ...")
    # We need diag data to know which patients are disallowed, so this is a
    # two-phase approach — first pass just collects notes and all patient IDs.
    notes_by_pid = {}
    doc = fitz.open(str(PDF_PATH))
    total = doc.page_count
    for i in range(total):
        if i % 10000 == 0 and i > 0:
            print(f"  {i:,}/{total:,} pages scanned", flush=True)
        try:
            rec = parse_page(doc[i].get_text())
            if rec and rec.get("PRIMARY INSURANCE"):
                pid = rec["EMR ID"].split(".")[0].strip()
                notes = rec.get("ENCOUNTER NOTES") or ""
                if notes:
                    notes_by_pid[pid] = notes
        except Exception:
            pass
    doc.close()
    print(f"  Notes collected for {len(notes_by_pid):,} patients")
    return notes_by_pid


# ---------------------------------------------------------------------------
# Step 2 — Identify disallowed patients using diag data
# ---------------------------------------------------------------------------

def get_insured_pids():
    """Scan PatientReport PDF and return set of EMR IDs that have PRIMARY INSURANCE."""
    print("Scanning PatientReport for insured patients ...")
    insured = set()
    doc = fitz.open(str(PDF_PATH))
    for i in range(doc.page_count):
        try:
            rec = parse_page(doc[i].get_text())
            if rec and rec.get("PRIMARY INSURANCE"):
                insured.add(rec["EMR ID"].split(".")[0].strip())
        except Exception:
            pass
    doc.close()
    print(f"  {len(insured):,} patients with primary insurance")
    return insured


def identify_disallowed(diag_patients, exact_icd, prefix_icd, insured_pids):
    """
    Returns set of EMR IDs (insured only) where _pick_primary_secondary returns
    a disallowed DX. Also returns full icd_map per pid for those patients.
    """
    disallowed_pids = set()
    icd_maps = {}
    for pid, icd_map in diag_patients.items():
        if pid not in insured_pids:
            continue
        flags = {}
        for icd, desc in icd_map.items():
            hit = _match_icd(icd, exact_icd, prefix_icd)
            if not hit and desc:
                hit = _desc_comorbidity(desc)
            if hit:
                flags[hit] = icd
        yes_list = [c for c in _COMORBIDITY_COLUMNS if c in flags]
        if not yes_list:
            continue
        pri, _ = _pick_primary_secondary(yes_list)
        if pri in _PRIMARY_DX_DISALLOWED:
            disallowed_pids.add(pid)
            icd_maps[pid] = icd_map
    return disallowed_pids, icd_maps


# ---------------------------------------------------------------------------
# Step 3 — Aggregate and summarise
# ---------------------------------------------------------------------------

def summarise(disallowed_pids, icd_maps, drug_patients, notes_by_pid,
              exact_icd, prefix_icd):

    total = len(disallowed_pids)
    print(f"\n{'='*60}")
    print(f"DISALLOWED-PRIMARY PATIENT ANALYSIS  (n={total:,})")
    print(f"{'='*60}")

    # --- ICD codes ---
    icd_counter        = Counter()   # raw code -> count
    icd_desc_map       = {}          # code -> description
    mapped_comorb      = Counter()   # comorbidity -> count (from ICD mapping)
    unmapped_icd       = Counter()   # ICD codes that don't map to any comorbidity

    for pid in disallowed_pids:
        icd_map = icd_maps.get(pid, {})
        for icd, desc in icd_map.items():
            icd_counter[icd] += 1
            if desc and icd not in icd_desc_map:
                icd_desc_map[icd] = desc
            hit = _match_icd(icd, exact_icd, prefix_icd)
            if not hit and desc:
                hit = _desc_comorbidity(desc)
            if hit:
                mapped_comorb[hit] += 1
            else:
                unmapped_icd[icd] += 1

    print(f"\n--- TOP 30 RAW ICD CODES (across {total:,} patients) ---")
    print(f"{'ICD':<12} {'Count':>7}  Description")
    print("-" * 60)
    for icd, cnt in icd_counter.most_common(30):
        desc = icd_desc_map.get(icd, '')[:45]
        print(f"{icd:<12} {cnt:>7,}  {desc}")

    print(f"\n--- MAPPED COMORBIDITIES PRESENT (ICD->comorbidity hits) ---")
    print(f"{'Comorbidity':<35} {'Patients':>8}")
    print("-" * 45)
    for comorb, cnt in mapped_comorb.most_common():
        marker = " *DISALLOWED*" if comorb in _PRIMARY_DX_DISALLOWED else ""
        print(f"{comorb:<35} {cnt:>8,}{marker}")

    print(f"\n--- TOP 20 UNMAPPED ICD CODES (coverage gaps) ---")
    print(f"{'ICD':<12} {'Count':>7}  Description")
    print("-" * 60)
    for icd, cnt in unmapped_icd.most_common(20):
        desc = icd_desc_map.get(icd, '')[:45]
        print(f"{icd:<12} {cnt:>7,}  {desc}")

    # --- Medications ---
    med_counter         = Counter()
    inferred_comorb_med = Counter()
    pids_with_meds      = 0

    for pid in disallowed_pids:
        rec = drug_patients.get(pid)
        if not rec:
            continue
        pids_with_meds += 1
        drugs = rec['current'] if rec['current'] else rec['all']
        for drug in drugs:
            med_counter[drug.lower()] += 1
            hit = _infer_comorb_from_drug(drug)
            if hit:
                inferred_comorb_med[hit] += 1

    print(f"\n--- TOP 30 MEDICATIONS ({pids_with_meds:,}/{total:,} patients have med data) ---")
    print(f"{'Medication':<45} {'Count':>7}")
    print("-" * 55)
    for med, cnt in med_counter.most_common(30):
        print(f"{med:<45} {cnt:>7,}")

    print(f"\n--- HEART CONDITIONS INFERRED FROM MEDICATIONS ---")
    print(f"{'Comorbidity':<35} {'Patients':>8}")
    print("-" * 45)
    for comorb, cnt in inferred_comorb_med.most_common():
        print(f"{comorb:<35} {cnt:>8,}")

    # --- Notes keyword scan ---
    NOTE_KEYWORDS = [
        'hypertension', 'htn', 'coronary', 'cad', 'arrhythmia', 'afib',
        'atrial fib', 'heart failure', 'chf', 'pacemaker', 'stent', 'bypass',
        'cabg', 'valve', 'cardiomyopathy', 'tachycardia', 'bradycardia',
        'peripheral vascular', 'stroke', 'hyperlipidemia', 'cholesterol',
        'diabetes', 'diabetic', 'obesity', 'obese', 'sleep apnea', 'copd',
        'chest pain', 'angina', 'shortness of breath', 'dyspnea',
        'echocardiogram', 'echo', 'stress test', 'catheterization',
        'ejection fraction', 'ef ', 'ablation', 'cardioversion',
    ]
    note_hits = Counter()
    pids_with_notes = 0
    for pid in disallowed_pids:
        notes = notes_by_pid.get(pid, '')
        if not notes:
            continue
        pids_with_notes += 1
        low = notes.lower()
        for kw in NOTE_KEYWORDS:
            if kw in low:
                note_hits[kw] += 1

    print(f"\n--- NOTE KEYWORD FREQUENCY ({pids_with_notes:,}/{total:,} patients have notes) ---")
    print(f"{'Keyword':<30} {'Patients':>8}  {'% of noted':>10}")
    print("-" * 55)
    for kw, cnt in note_hits.most_common():
        pct = cnt * 100 / pids_with_notes if pids_with_notes else 0
        print(f"{kw:<30} {cnt:>8,}  {pct:>9.1f}%")

    # --- Summary verdict ---
    heart_icd_count = sum(
        cnt for comorb, cnt in mapped_comorb.items()
        if comorb not in _PRIMARY_DX_DISALLOWED
    )
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Patients analysed          : {total:,}")
    print(f"  Have NON-disallowed ICD hit : {heart_icd_count:,}  "
          f"(patients who DO have a mappable heart condition)")
    print(f"  Have medication heart hint  : {sum(inferred_comorb_med.values()):,}")
    pct_notes_heart = (
        note_hits.get('hypertension', 0) + note_hits.get('htn', 0) +
        note_hits.get('coronary', 0) + note_hits.get('cad', 0) +
        note_hits.get('arrhythmia', 0) + note_hits.get('afib', 0) +
        note_hits.get('heart failure', 0) + note_hits.get('chf', 0)
    )
    print(f"  Notes mention heart term    : {pct_notes_heart:,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not PDF_PATH or not PDF_PATH.exists():
        print("ERROR: PatientReport PDF not found."); sys.exit(1)
    if not DIAG_PDF_PATH or not DIAG_PDF_PATH.exists():
        print("ERROR: DetailedDiagnosisAnalysis PDF not found."); sys.exit(1)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    exact_icd, prefix_icd, _ = _load_api_mappings(API_CAUSE_CSV)

    # Extract diag + drugs CSVs (parallel if both present)
    from concurrent.futures import ThreadPoolExecutor
    tasks = {}
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks['diag']  = pool.submit(extract_diag_to_csv,  DIAG_PDF_PATH,  ts)
        if DRUGS_PDF_PATH and DRUGS_PDF_PATH.exists():
            tasks['drugs'] = pool.submit(extract_drugs_to_csv, DRUGS_PDF_PATH, ts)

    diag_csv  = tasks['diag'].result()
    drugs_csv = tasks['drugs'].result() if 'drugs' in tasks else None

    print("Parsing diagnosis CSV ...")
    diag_patients = parse_diag_csv(diag_csv)
    print(f"  {len(diag_patients):,} patients with diagnosis data")

    drug_patients = {}
    if drugs_csv:
        print("Parsing medications CSV ...")
        drug_patients = parse_drugs_csv(drugs_csv)
        print(f"  {len(drug_patients):,} patients with medication data")

    insured_pids = get_insured_pids()

    print("\nIdentifying disallowed-primary patients ...")
    disallowed_pids, icd_maps = identify_disallowed(diag_patients, exact_icd, prefix_icd, insured_pids)
    print(f"  {len(disallowed_pids):,} patients with disallowed-only primary DX")

    print("\nScanning PatientReport for encounter notes ...")
    notes_by_pid = scan_patient_report(exact_icd, prefix_icd)

    summarise(disallowed_pids, icd_maps, drug_patients, notes_by_pid,
              exact_icd, prefix_icd)

    # Clean up
    for f in CLEANED_DIR.glob("*.csv"):
        try: f.unlink()
        except Exception: pass


if __name__ == "__main__":
    main()
