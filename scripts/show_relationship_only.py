import pandas as pd
import re
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HBOX = REPO / 'src' / 'CIM' / 'Final_Hbox_3_19_26.xlsx'

REL_KEYWORDS = ['son','dau','daughter','wife','husb','husband','mom','mother','dad','father','bro','brother','sis','sister','frie','friend','nephew','niece','other','spouse','self','guardian','grand','step','aunt','uncle','cousin','ex','none','in-law','room','roommate']

punc_re = re.compile(r"[\.,;:\(\)\[\]\"']")

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
    'othe': 'Other',
    'spouse': 'Spouse',
    'self': 'Self',
    'guardian': 'Guardian',
    'grandson': 'Grandson',
    'granddaughter': 'Granddaughter',
    'aunt': 'Aunt',
    'uncle': 'Uncle',
    'cousin': 'Cousin'
}


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


def looks_like_relationship(raw):
    if raw is None:
        return False
    r = str(raw).strip().lower()
    if not r:
        return False
    # if contains comma it's likely a name
    if ',' in r:
        return False
    # if contains digits, skip
    if re.search(r'\d', r):
        return False
    # check for any keyword
    for k in REL_KEYWORDS:
        if k in r:
            return True
    # also accept short words (<=2 tokens) that are not names
    toks = r.split()
    if len(toks) <= 2 and len(r) <= 20:
        # exclude single capitalized words that look like names? keep conservative
        return True
    return False


def main():
    if not HBOX.exists():
        print('Hbox file not found:', HBOX)
        return
    df = pd.read_excel(HBOX, sheet_name='Sheet1', engine='openpyxl')
    cols = [c for c in df.columns if isinstance(c, str) and any(k in c.lower() for k in ['emer','emerg','contact','rel'])]
    raw_vals = set()
    for c in cols:
        for v in df[c].dropna().unique():
            rv = str(v).strip()
            if rv and looks_like_relationship(rv):
                raw_vals.add(rv)
    mapping = {rv: normalize_relationship(rv) for rv in sorted(raw_vals)}
    print(json.dumps(mapping, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
