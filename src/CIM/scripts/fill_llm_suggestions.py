#!/usr/bin/env python3
"""Fill `llm_suggested_cause` and `llm_suggested_icd` in a copy of the
`problem_list_llm_mapping_*.csv` using available candidates and fuzzy matching
against the canonical disease list. Produces a new file with suffix
`_filled_YYYYMMDD_HHMMSS.csv` and does not overwrite existing files.
"""
import csv
import datetime
import glob
import os
import sys
from difflib import SequenceMatcher


MAPPINGS_DIR = os.path.join('src', 'CIM', 'mappings')
Disease_PATH = os.path.join('src', 'CIM', 'disease', 'api_prescriptioncauselist_202603101243.csv')


def find_latest_llm_mapping():
    pattern = os.path.join(MAPPINGS_DIR, 'problem_list_llm_mapping_*.csv')
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort()
    return files[-1]


def load_diseases(path):
    diseases = []
    if not os.path.exists(path):
        return diseases
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader, None)
        for row in reader:
            if not row:
                continue
            name = row[0].strip()
            icd = row[1].strip() if len(row) > 1 else ''
            diseases.append((name, icd))
    return diseases


def best_fuzzy_match(token, diseases, min_ratio=0.6):
    t = token.lower()
    best = (None, None, 0.0)
    for name, icd in diseases:
        ratio = SequenceMatcher(None, t, name.lower()).ratio()
        if ratio > best[2]:
            best = (name, icd, ratio)
    if best[2] >= min_ratio:
        return best[0], best[1], best[2]
    return None, None, best[2]


def main():
    src = find_latest_llm_mapping()
    if not src:
        print('No LLm mapping file found in', MAPPINGS_DIR)
        sys.exit(1)

    diseases = load_diseases(Disease_PATH)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    base = os.path.basename(src)
    out_name = base.replace('.csv', f'_filled_{ts}.csv')
    out_path = os.path.join(MAPPINGS_DIR, out_name)

    with open(src, newline='', encoding='utf-8') as fin, \
         open(out_path, 'w', newline='', encoding='utf-8') as fout:
        reader = csv.DictReader(fin)
        fieldnames = reader.fieldnames
        if fieldnames is None:
            print('Source file has no header')
            sys.exit(1)
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            tok = (row.get('token') or '').strip()
            # If already filled, keep
            if (row.get('llm_suggested_cause') or '').strip():
                writer.writerow(row)
                continue

            # Prefer candidate 1 if present
            cand1 = (row.get('candidate_1_name') or '').strip()
            cand1_icd = (row.get('candidate_1_icd') or '').strip()
            if cand1:
                row['llm_suggested_cause'] = cand1
                row['llm_suggested_icd'] = cand1_icd
                row['notes'] = (row.get('notes') or '') + 'filled_from_candidate_1'
                writer.writerow(row)
                continue

            # fallback to fuzzy matching against diseases
            name, icd, ratio = best_fuzzy_match(tok, diseases, min_ratio=0.55)
            if name:
                row['llm_suggested_cause'] = name
                row['llm_suggested_icd'] = icd
                row['notes'] = (row.get('notes') or '') + f'filled_fuzzy_{ratio:.2f}'
            else:
                row['notes'] = (row.get('notes') or '') + f'no_match_best_ratio_{ratio:.2f}'
            writer.writerow(row)

    print(out_path)


if __name__ == '__main__':
    main()
