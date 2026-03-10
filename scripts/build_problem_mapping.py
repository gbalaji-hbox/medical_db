import os
import re
import pandas as pd

BASE = os.path.dirname(os.path.dirname(__file__))
HBOX_PATH = os.path.join(BASE, 'Hbox list 3 9 26.xlsx')
DISEASE_CSV = os.path.join(BASE, 'disease', 'api_prescriptioncauselist_202603101243.csv')
OUT_DIR = os.path.join(BASE, 'mappings')
OUT_CSV = os.path.join(OUT_DIR, 'problem_list_mapping.csv')
OUT_SUGGEST = os.path.join(OUT_DIR, 'problem_primary_suggestions.csv')
CAUSE_SEVERITY = os.path.join(os.path.dirname(__file__), '..', 'mappings', 'cause_severity.csv')

SEPARATORS = re.compile(r'[;,|/\\\n]+')


def split_tokens(text):
    if pd.isna(text):
        return []
    return [t.strip() for t in SEPARATORS.split(str(text)) if t.strip()]


def load_diseases(path):
    df = pd.read_csv(path)
    df['cause_norm'] = df['cause'].str.strip().str.lower()
    df['icd_norm'] = df['icd_code'].astype(str).str.strip().str.lower()
    return df


def match_token(token, disease_df):
    tl = token.lower()
    # exact cause substring match
    for _, r in disease_df.iterrows():
        if r['cause_norm'] and r['cause_norm'] in tl:
            return r['cause'], r['icd_code'], 'cause_name'
    # icd code in token
    for _, r in disease_df.iterrows():
        icd = str(r['icd_code']).lower()
        if icd and icd in tl:
            return r['cause'], r['icd_code'], 'icd'
    return None, None, 'none'


def load_severity(path):
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    res = {str(r['cause']).strip().lower(): float(r.get('severity') or 0) for _, r in df.iterrows()}
    return res


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    disease_df = load_diseases(DISEASE_CSV)
    hbox_df = pd.read_excel(HBOX_PATH, sheet_name='Sheet1', engine='openpyxl')
    tokens_set = set()
    for _, r in hbox_df.iterrows():
        plist = r.get('Problem List')
        if pd.isna(plist):
            continue
        tokens = split_tokens(plist)
        for t in tokens:
            tokens_set.add(t)
    rows = []
    for t in sorted(tokens_set):
        cause, icd, method = match_token(t, disease_df)
        rows.append({'token': t, 'matched_cause': cause or '', 'icd_code': icd or '', 'match_method': method})
    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_CSV, index=False)
    print(f'Wrote mapping CSV to: {OUT_CSV}')

    # now build per-row suggestions using severity
    severity_map = load_severity(CAUSE_SEVERITY)
    suggestions = []
    for _, r in hbox_df.iterrows():
        plist = r.get('Problem List')
        if pd.isna(plist):
            continue
        tokens = split_tokens(plist)
        matched = []
        for t in tokens:
            cause, icd, method = match_token(t, disease_df)
            if cause:
                matched.append({'token': t, 'cause': cause, 'icd': icd, 'method': method})
        # determine suggested primary/secondary by severity
        suggested_primary = ''
        suggested_secondary = ''
        if matched:
            # respect explicit labels
            prims = [m for m in matched if 'primary' in m['token'].lower()]
            secs = [m for m in matched if 'secondary' in m['token'].lower()]
            if prims:
                suggested_primary = prims[0]['cause']
            if secs:
                suggested_secondary = secs[0]['cause']
            if not suggested_primary:
                # sort matched causes by severity
                uniq = {}
                for m in matched:
                    c = m['cause']
                    if c not in uniq:
                        uniq[c] = severity_map.get(c.strip().lower(), 0)
                sorted_causes = sorted(uniq.items(), key=lambda x: x[1], reverse=True)
                if sorted_causes:
                    suggested_primary = sorted_causes[0][0]
                    if len(sorted_causes) > 1:
                        suggested_secondary = sorted_causes[1][0]
        suggestions.append({
            'MRN': r.get('MRN'),
            'Patient': r.get('Patient'),
            'Problem List': plist,
            'matched_causes': '|'.join([m['cause'] for m in matched]),
            'suggested_primary': suggested_primary,
            'suggested_secondary': suggested_secondary
        })
    sug_df = pd.DataFrame(suggestions)
    sug_df.to_csv(OUT_SUGGEST, index=False)
    print(f'Wrote suggestions CSV to: {OUT_SUGGEST}')

if __name__ == '__main__':
    main()
