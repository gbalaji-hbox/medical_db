import pandas as pd
import re
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HBOX = REPO / 'src' / 'CIM' / 'Final_Hbox_3_19_26.xlsx'

SEEK_KEYS = ['emer', 'emerg', 'contact', 'rel']

norm_map = {
    'son': 'Son',
    'dau': 'Daughter',
    'daug': 'Daughter',
    'daughter': 'Daughter',
    'wife': 'Wife',
    'husb': 'Husband',
    'husband': 'Husband',
    'mom': 'Mother',
    'mother': 'Mother',
    'dad': 'Father',
    'father': 'Father',
    'bro': 'Brother',
    'brother': 'Brother',
    'sis': 'Sister',
    'sister': 'Sister',
    'frie': 'Friend',
    'friend': 'Friend',
    'neph': 'Nephew',
    'niece': 'Niece',
    'other': 'Other',
    'spouse': 'Spouse',
    'self': 'Self',
    'guardian': 'Guardian',
    'grandson': 'Grandson',
    'granddaughter': 'Granddaughter'
}

punc_re = re.compile(r"[\.,;:\(\)\[\]\"']")


def normalize_relationship(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    s_clean = punc_re.sub('', s).strip()
    key = s_clean.lower()
    if key in norm_map:
        return norm_map[key]
    first = key.split()[0]
    if first in norm_map:
        return norm_map[first]
    return s_clean.title()


def main():
    if not HBOX.exists():
        print('Hbox file not found:', HBOX)
        return
    df = pd.read_excel(HBOX, sheet_name='Sheet1', engine='openpyxl')
    cols = [c for c in df.columns if isinstance(c, str) and any(k in c.lower() for k in SEEK_KEYS)]
    raw_vals = set()
    for c in cols:
        for v in df[c].dropna().unique():
            rv = str(v).strip()
            if rv:
                raw_vals.add(rv)
    mapping = {rv: normalize_relationship(rv) for rv in sorted(raw_vals)}
    print(json.dumps(mapping, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
