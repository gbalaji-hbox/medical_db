import os
import re
import pandas as pd
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA = os.path.join(ROOT, 'data_new.xlsx')
OUT_DIR = os.path.join(ROOT, 'mappings')
OUT = os.path.join(OUT_DIR, 'problem_list_frequency.csv')

SEPARATORS = re.compile(r'[;,|/\\\n]+')

def split_tokens(text):
    if pd.isna(text):
        return []
    return [t.strip() for t in SEPARATORS.split(str(text)) if t.strip()]

def main():
    if not os.path.exists(DATA):
        print('data file not found:', DATA)
        return
    df = pd.read_excel(DATA, sheet_name=0, engine='openpyxl')
    counter = Counter()
    for s in df.get('Problem List', pd.Series()).dropna().astype(str):
        for t in split_tokens(s):
            norm = t.strip()
            if norm:
                counter[norm] += 1

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, 'w', encoding='utf8') as f:
        f.write('token,count\n')
        for token, cnt in counter.most_common():
            token_esc = token.replace('"', '""')
            f.write(f'"{token_esc}",{cnt}\n')

    print('WROTE', OUT)
    # print top 50
    for t, c in counter.most_common(50):
        print(f'{c:6d}  {t}')

if __name__ == '__main__':
    main()
