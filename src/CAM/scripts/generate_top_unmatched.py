#!/usr/bin/env python3
"""Generate a timestamped CSV of top unmatched Problem List tokens.

Reads `src/CIM/mappings/problem_list_frequency.csv` and compares tokens
against existing mapping files to produce a file `problem_list_top_unmatched_YYYYMMDD_HHMMSS.csv`.
"""
import csv
import datetime
import os
import sys


FREQ_PATH = os.path.join('src', 'CIM', 'mappings', 'problem_list_frequency.csv')
MAP_PATHS = [
    os.path.join('src', 'CIM', 'mappings', 'problem_list_mapping.csv'),
    os.path.join('src', 'CIM', 'mappings', 'problem_list_llm_mapping.csv'),
]


def load_mapped_tokens(paths):
    tokens = set()
    for p in paths:
        if not os.path.exists(p):
            continue
        try:
            with open(p, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # If file lacks header, DictReader will use first row as header; handle defensively
                for row in reader:
                    if not row:
                        continue
                    key = None
                    if 'token' in row and row['token'] is not None:
                        key = row['token']
                    else:
                        # fallback: first column value
                        vals = list(row.values())
                        if vals:
                            key = vals[0]
                    if not key:
                        continue
                    key = str(key).strip().strip('"').strip("'").lower()
                    if key:
                        tokens.add(key)
        except Exception:
            # best-effort: skip unreadable mapping
            continue
    return tokens


def load_frequency(path):
    items = []
    if not os.path.exists(path):
        return items
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tok = row.get('token') or ''
            cnt = row.get('count') or row.get('cnt') or '0'
            try:
                cnt = int(cnt)
            except Exception:
                try:
                    cnt = int(float(cnt))
                except Exception:
                    cnt = 0
            tok = str(tok).strip().strip('"').strip("'")
            items.append((tok, cnt))
    return items


def is_noise(token_lower):
    noise = {
        'unspecified', 'unknown', 's', 'h', 'left', 'right', 'bilateral',
        'adult', 'initial encounter', 'initial', 'other', 'benign', 'essential'
    }
    if not token_lower:
        return True
    if token_lower in noise:
        return True
    if len(token_lower) <= 2:
        return True
    return False


def main():
    mapped = load_mapped_tokens(MAP_PATHS)
    freq = load_frequency(FREQ_PATH)
    unmatched = []
    for tok, cnt in freq:
        key = tok.strip().lower()
        if key in mapped:
            continue
        if is_noise(key):
            continue
        unmatched.append((tok, cnt))

    # already sorted in frequency file; keep order and take top N
    top_n = unmatched[:200]
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    out_name = f'problem_list_top_unmatched_{ts}.csv'
    out_path = os.path.join('src', 'CIM', 'mappings', out_name)
    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['token', 'count'])
        for tok, cnt in top_n:
            writer.writerow([tok, cnt])

    print(out_path)


if __name__ == '__main__':
    main()
