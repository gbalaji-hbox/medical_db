#!/usr/bin/env python3
"""Generate a timestamped LLM mapping CSV for top unmatched tokens.

Reads `problem_list_top_unmatched_*.csv` (the most recent), and the canonical
disease list `src/CIM/disease/api_prescriptioncauselist_202603101243.csv` to
produce `problem_list_llm_mapping_YYYYMMDD_HHMMSS.csv` with candidate matches.
"""
import csv
import datetime
import glob
import os
import sys


MAPPINGS_DIR = os.path.join('src', 'CIM', 'mappings')
Disease_PATH = os.path.join('src', 'CIM', 'disease', 'api_prescriptioncauselist_202603101243.csv')


def find_latest_top_unmatched():
    pattern = os.path.join(MAPPINGS_DIR, 'problem_list_top_unmatched_*.csv')
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort()
    return files[-1]


def load_diseases(path):
    # Expecting columns with a cause name and optional ICD; be permissive
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


def candidate_matches(token, diseases):
    t = token.lower()
    candidates = []
    for name, icd in diseases:
        nl = name.lower()
        if t == nl:
            candidates.insert(0, (name, icd, 'exact'))
        elif t in nl or nl in t:
            candidates.append((name, icd, 'substring'))
    return candidates[:5]


def main():
    top_file = find_latest_top_unmatched()
    if not top_file:
        print('No top-unmatched file found in', MAPPINGS_DIR)
        sys.exit(1)

    diseases = load_diseases(Disease_PATH)

    out_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out_name = f'problem_list_llm_mapping_{out_ts}.csv'
    out_path = os.path.join(MAPPINGS_DIR, out_name)

    with open(top_file, newline='', encoding='utf-8') as fin, \
         open(out_path, 'w', newline='', encoding='utf-8') as fout:
        reader = csv.DictReader(fin)
        fieldnames = [
            'token', 'count',
            'candidate_1_name', 'candidate_1_icd', 'candidate_1_matchtype',
            'candidate_2_name', 'candidate_2_icd', 'candidate_2_matchtype',
            'candidate_3_name', 'candidate_3_icd', 'candidate_3_matchtype',
            'candidate_4_name', 'candidate_4_icd', 'candidate_4_matchtype',
            'candidate_5_name', 'candidate_5_icd', 'candidate_5_matchtype',
            'llm_suggested_cause', 'llm_suggested_icd', 'notes'
        ]
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()
        for row in reader:
            tok = row.get('token','').strip()
            cnt = row.get('count','')
            candidates = candidate_matches(tok, diseases)
            out = {'token': tok, 'count': cnt}
            for i in range(5):
                key_name = f'candidate_{i+1}_name'
                key_icd = f'candidate_{i+1}_icd'
                key_mt = f'candidate_{i+1}_matchtype'
                if i < len(candidates):
                    name, icd, mt = candidates[i]
                    out[key_name] = name
                    out[key_icd] = icd
                    out[key_mt] = mt
                else:
                    out[key_name] = ''
                    out[key_icd] = ''
                    out[key_mt] = ''
            out['llm_suggested_cause'] = ''
            out['llm_suggested_icd'] = ''
            out['notes'] = ''
            writer.writerow(out)

    print(out_path)


if __name__ == '__main__':
    main()
