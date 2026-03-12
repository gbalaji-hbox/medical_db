#!/usr/bin/env python3
"""Merge filled LLM mapping into main `problem_list_mapping.csv`.

Rules:
- Find the most recent `problem_list_llm_mapping_*_filled_*.csv` file.
- For rows with `llm_suggested_cause`, add or update the main mapping.
- Do NOT overwrite existing `matched_cause` unless it is empty or 'none'.
- Backup the original mapping to `problem_list_mapping_backup_YYYYMMDD_HHMMSS.csv`.
"""
import csv
import datetime
import glob
import os
import shutil
import sys


MAPPINGS_DIR = os.path.join('src', 'CIM', 'mappings')
MAIN_MAP = os.path.join(MAPPINGS_DIR, 'problem_list_mapping.csv')


def find_latest_filled():
    pattern = os.path.join(MAPPINGS_DIR, 'problem_list_llm_mapping_*_filled_*.csv')
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort()
    return files[-1]


def load_main(path):
    rows = {}
    if not os.path.exists(path):
        return rows
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            tok = (r.get('token') or '').strip().lower()
            rows[tok] = r
    return rows


def main():
    filled = find_latest_filled()
    if not filled:
        print('No filled LLM mapping file found in', MAPPINGS_DIR)
        sys.exit(1)

    main_map = load_main(MAIN_MAP)
    # backup
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    if os.path.exists(MAIN_MAP):
        bk = os.path.join(MAPPINGS_DIR, f'problem_list_mapping_backup_{ts}.csv')
        shutil.copy2(MAIN_MAP, bk)
        print('Backed up main mapping to', bk)

    # read filled rows
    updates = 0
    additions = 0
    with open(filled, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            tok = (r.get('token') or '').strip()
            if not tok:
                continue
            key = tok.lower()
            suggested = (r.get('llm_suggested_cause') or '').strip()
            suggested_icd = (r.get('llm_suggested_icd') or '').strip()
            if not suggested:
                continue
            if key in main_map:
                existing = main_map[key]
                existing_cause = (existing.get('matched_cause') or '').strip()
                if not existing_cause or existing_cause.lower() in ('', 'none', 'nan'):
                    existing['matched_cause'] = suggested
                    existing['icd_code'] = suggested_icd
                    existing['match_method'] = 'llm_suggested'
                    updates += 1
                else:
                    # leave existing
                    continue
            else:
                main_map[key] = {
                    'token': tok,
                    'matched_cause': suggested,
                    'icd_code': suggested_icd,
                    'match_method': 'llm_suggested',
                    'method': '',
                    'notes': ''
                }
                additions += 1

    # write merged mapping (overwrite MAIN_MAP)
    fieldnames = ['token', 'matched_cause', 'icd_code', 'match_method', 'method', 'notes']
    tmp_out = os.path.join(MAPPINGS_DIR, f'problem_list_mapping_merged_{ts}.csv')
    with open(tmp_out, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for k, r in sorted(main_map.items()):
            out = {fn: r.get(fn, '') for fn in fieldnames}
            writer.writerow(out)

    # move merged to MAIN_MAP (atomic)
    shutil.copy2(tmp_out, MAIN_MAP)
    print(f'Wrote merged mapping to {MAIN_MAP} (updated {updates}, added {additions})')
    print('Merged source:', filled)


if __name__ == '__main__':
    main()
