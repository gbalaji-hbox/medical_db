import re
import os
import sys
import pandas as pd
from datetime import datetime
# Ensure repo root is on sys.path so `constants` can be imported when running from `scripts/`
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
CIM_ROOT = os.path.join(REPO_ROOT, 'src', 'CIM')
if CIM_ROOT not in sys.path:
    sys.path.insert(0, CIM_ROOT)
import constants

BASE = os.path.dirname(os.path.dirname(__file__))
HBOX_PATH = os.path.join(CIM_ROOT, 'Hbox list 3 9 26.xlsx')
TEMPLATE_PATH = os.path.join(CIM_ROOT, 'template', 'consolidated_view-template.xlsx')
DISEASE_CSV = os.path.join(CIM_ROOT, 'disease', 'api_prescriptioncauselist_202603101243.csv')
CAUSE_SEVERITY = os.path.join(CIM_ROOT, 'mappings', 'cause_severity.csv')
OUTPUT_DIR = os.path.join(CIM_ROOT, 'output')
OUTPUT_XLSX = os.path.join(OUTPUT_DIR, 'consolidated_filled.xlsx')

PHONE_LABELS = {
    'home': ['hm', 'home'],
    'work': ['wk', 'work', 'wrk'],
    'mobile': ['cell', 'mobile', 'mb', 'm']
}

SEPARATORS = re.compile(r'[;,|/\\\n]+')
NUM_RE = re.compile(r"(\+?\d[\d\-\s\(\)]{6,}\d)")


def load_diseases(path):
    df = pd.read_csv(path)
    # normalize cause names
    df['cause_norm'] = df['cause'].str.strip().str.lower()
    df['icd_norm'] = df['icd_code'].astype(str).str.strip().str.lower()
    return df


def load_severity_map(path):
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    return {str(r['cause']).strip().lower(): float(r.get('severity') or 0) for _, r in df.iterrows()}


def split_tokens(text):
    if pd.isna(text):
        return []
    return [t.strip() for t in SEPARATORS.split(str(text)) if t.strip()]


def find_disease_matches(tokens, disease_df):
    matches = []  # list of dicts {cause, icd, token, is_primary, is_secondary}
    for token in tokens:
        tl = token.lower()
        is_primary = 'primary' in tl
        is_secondary = 'secondary' in tl
        # match by cause name or icd
        found = False
        for _, r in disease_df.iterrows():
            cause = r['cause']
            cause_norm = r['cause_norm']
            icd = str(r['icd_code']).lower()
            if cause_norm and cause_norm in tl:
                matches.append({'cause': cause, 'icd': icd, 'token': token, 'is_primary': is_primary, 'is_secondary': is_secondary})
                found = True
                break
            if icd and icd in tl:
                matches.append({'cause': cause, 'icd': icd, 'token': token, 'is_primary': is_primary, 'is_secondary': is_secondary})
                found = True
                break
        # no partial/ICD match -> continue
    return matches


def phone_parts(cell):
    # returns dict with possible keys: home, mobile, work
    out = {'home': None, 'mobile': None, 'work': None}
    if pd.isna(cell):
        return out
    parts = SEPARATORS.split(str(cell))
    for p in parts:
        pl = p.strip()
        if not pl:
            continue
        num_m = NUM_RE.search(pl)
        num = num_m.group(1).strip() if num_m else pl.strip()
        lower = pl.lower()
        assigned = False
        for key, labels in PHONE_LABELS.items():
            for lab in labels:
                if re.search(r'\b' + re.escape(lab) + r'\b', lower):
                    out[key] = num
                    assigned = True
                    break
            if assigned:
                break
        if not assigned:
            # unlabeled: heuristics
            digits = re.sub(r'\D', '', num)
            if len(digits) >= 10:
                out['mobile'] = out['mobile'] or num
            else:
                out['home'] = out['home'] or num
    return out


def parse_next_appt(cell):
    if pd.isna(cell):
        return None, None
    s = str(cell)
    # attempt to find a date-like substring
    # common format: 2026-03-12 or mm/dd/yyyy etc. fallback: split tokens, last token provider
    date = None
    provider = None
    # try ISO date
    iso = re.search(r'(\d{4}-\d{2}-\d{2})', s)
    if iso:
        date = iso.group(1)
        # provider is rest after date
        provider = s.replace(iso.group(0), '').strip(' ,-;:')
        return date, provider if provider else None
    # try mm/dd/yyyy
    m = re.search(r'(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', s)
    if m:
        date = m.group(1)
        provider = s.replace(m.group(0), '').strip(' ,-;:')
        return date, provider if provider else None
    # fallback: split by separators, if last token looks like a name assume provider
    parts = SEPARATORS.split(s)
    if len(parts) >= 2:
        # guess: last is provider
        provider = parts[-1].strip()
        # try to find date in other parts
        for p in parts:
            if re.search(r'\d{4}-\d{2}-\d{2}', p) or re.search(r'\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}', p):
                date = p.strip()
                break
    return date, provider


def clean_provider_name(s):
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    # remove parenthetical groups that contain digits, e.g. "Dr X (12345)"
        s = re.sub(r"\s*\([^\)]*\d+[^\)]*\)", "", s)
    # remove bracketed numeric groups
    s = re.sub(r"\s*\[[^\]]*\d+[^\]]*\]", "", s)
    # remove trailing separators followed by numeric id: " - 12345", "|12345"
    s = re.sub(r"[\-|\|,:]\s*ID[:\s]*\d+\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[\-|\|:,]\s*\d{3,}\s*$", "", s)
    # remove common "ID" suffixes
    s = re.sub(r"\bID\b[:\s]*\d+\s*$", "", s, flags=re.IGNORECASE)
    return s.strip()


def format_provider_person(s):
    """Given a provider string like 'Ajjour, Mohamad K, MD' or 'Mohamad K Ajjour, MD',
    return 'First Last' (e.g. 'Mohamad Ajjour')."""
    if s is None:
        return ''
    s = clean_provider_name(s)
    if not s:
        return ''
    # if comma-separated like 'Last, First ...'
    if ',' in s:
        parts = [p.strip() for p in s.split(',') if p.strip()]
        if len(parts) >= 2:
            last = parts[0]
            first_part = parts[1]
            first_name = first_part.split()[0] if first_part else ''
            if first_name:
                return f"{first_name} {last}"
            return last
    # otherwise try to take first and last tokens
    toks = s.split()
    if len(toks) >= 2:
        first = toks[0]
        last = toks[-1]
        return f"{first} {last}"
    return s


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    disease_df = load_diseases(DISEASE_CSV)

    # read template headers
    template_df = pd.read_excel(TEMPLATE_PATH, sheet_name=0, nrows=0, engine='openpyxl')
    template_cols = list(template_df.columns)

    # read hbox file (streaming handled by pandas for large file)
    hbox_df = pd.read_excel(HBOX_PATH, sheet_name='Sheet1', engine='openpyxl')

    # normalize column names (strip)
    hbox_df.columns = [c.strip() if isinstance(c, str) else c for c in hbox_df.columns]

    # precompute matches per row
    matches_col = []
    for _, r in hbox_df.iterrows():
        tokens = split_tokens(r.get('Problem List', ''))
        matches = find_disease_matches(tokens, disease_df)
        matches_col.append(matches)
    hbox_df['_disease_matches'] = matches_col

    # group by MRN for cross-row secondary assignment
    groups = hbox_df.groupby('MRN') if 'MRN' in hbox_df.columns else hbox_df.groupby('MRN')

    # prepare output rows
    out_rows = []
    for mrn, group in groups:
        # collect distinct causes across group preserving Last Visit Date order (most recent first)
        group = group.copy()
        # parse last visit date to datetime for ordering
        if 'Last Visit Date' in group.columns:
            def parse_date(x):
                try:
                    return pd.to_datetime(x)
                except Exception:
                    return pd.NaT
            group['_last_seen_dt'] = group['Last Visit Date'].apply(parse_date)
            group = group.sort_values('_last_seen_dt', ascending=False)
        else:
            group['_last_seen_dt'] = pd.NaT

        distinct_causes = []
        for _, row in group.iterrows():
            for m in row['_disease_matches']:
                if m['cause'] not in distinct_causes:
                    distinct_causes.append(m['cause'])

        # process each row in the group
        for _, row in group.iterrows():
            out = {c: None for c in template_cols}
            # direct mappings
            out['EMR_ID'] = row.get('MRN')
            # preserve original EMR name field
            out['PATIENT_EMR_NAME'] = row.get('Patient')
            # Patient name handling: Hbox `Patient` may be "Last, First". Prefer explicit first/last columns if present.
            patient_field = row.get('Patient')
            first_col = row.get('Patient First Name')
            last_col = row.get('Patient Last Name')
            if pd.notna(first_col) and pd.notna(last_col) and str(first_col).strip() and str(last_col).strip():
                out['FIRST_NAME'] = str(first_col).strip()
                out['LAST_NAME'] = str(last_col).strip()
                out['PATIENT_FULL_NAME'] = f"{out['FIRST_NAME']} {out['LAST_NAME']}"
            else:
                # parse `Patient` which is usually "Last, First"
                if isinstance(patient_field, str) and ',' in patient_field:
                    last, rest = [p.strip() for p in patient_field.split(',', 1)]
                    first = rest
                    first_token = first.split()[0] if first else ''
                    out['FIRST_NAME'] = first_token
                    out['LAST_NAME'] = last
                    out['PATIENT_FULL_NAME'] = f"{out['FIRST_NAME']} {out['LAST_NAME']}".strip()
                else:
                    # fallback: try splitting on whitespace
                    if isinstance(patient_field, str):
                        parts = patient_field.split()
                        if len(parts) >= 2:
                            out['FIRST_NAME'] = parts[0]
                            out['LAST_NAME'] = ' '.join(parts[1:])
                            out['PATIENT_FULL_NAME'] = f"{out['FIRST_NAME']} {out['LAST_NAME']}"
                        else:
                            out['PATIENT_FULL_NAME'] = patient_field
                    # also fill from explicit columns if available
                    if not out.get('FIRST_NAME') and pd.notna(first_col):
                        out['FIRST_NAME'] = str(first_col).strip()
                    if not out.get('LAST_NAME') and pd.notna(last_col):
                        out['LAST_NAME'] = str(last_col).strip()
            out['DATE_OF_BIRTH'] = row.get('DOB')
            out['GENDER'] = row.get('Sex')
            # street address concat: prefer `Street Address` then `Street Address Ln 3`.
            sa = row.get('Street Address') if 'Street Address' in row else None
            sa3 = row.get('Street Address Ln 3') if 'Street Address Ln 3' in row else None
            if pd.notna(sa) and str(sa).strip():
                if pd.notna(sa3) and str(sa3).strip():
                    out['STREET_ADDRESS'] = f"{str(sa).strip()}, {str(sa3).strip()}"
                else:
                    out['STREET_ADDRESS'] = str(sa).strip()
            else:
                # fallback: scan for address-like columns but exclude email fields
                addr_parts = []
                for col in row.index:
                    if not isinstance(col, str):
                        continue
                    low = col.lower()
                    if 'address' in low and 'city' not in low and 'zip' not in low:
                        # exclude email/e-mail columns
                        if 'email' in low or 'e-mail' in low:
                            continue
                        v = row.get(col)
                        if pd.notna(v) and str(v).strip():
                            addr_parts.append(str(v).strip())
                out['STREET_ADDRESS'] = ', '.join(addr_parts) if addr_parts else None
            out['CITY'] = row.get('Pt City')
            out['ZIP'] = row.get('ZIP')
            out['EMAIL_ADDRESS'] = row.get('Pt. E-mail Address')
            out['LANGUAGE'] = row.get('Language')
            out['EMERGENCY_CONTACT_NAME'] = row.get('Emergency Contact Name')

            # phones
            phone = row.get('Phone')
            ph = phone_parts(phone)
            out['HOME_PHONE'] = ph.get('home')
            out['MOBILE_PHONE'] = ph.get('mobile')
            out['WORK_PHONE'] = ph.get('work')
            # emergency contact phone
            ec_ph = phone_parts(row.get('Emerg Contact Ph'))
            out['EMERGENCY_CONTACT_HOME_PHONE'] = ec_ph.get('home')
            out['EMERGENCY_CONTACT_MOBILE_PHONE'] = ec_ph.get('mobile')

            # insurance
            out['PRIMARY_INSURANCE'] = row.get('Primary Cvg') or row.get('Primary Payer')
            out['PRIMARY_ID'] = row.get('Primary Mem ID') or row.get('Medicare Sub ID')
            out['SECONDARY_INSURANCE'] = row.get('Secondary Cvg') or row.get('Secondary Payer')
            out['SECONDARY_ID'] = row.get('Pat Secondary CVG Payer ID')
            out['TERITARY_INSURANCE'] = row.get('Tertiary Payer')
            out['TERITARY_ID'] = row.get('Tertiary Mem ID') or row.get('Pat Tertiary CVG Payer ID')
            out['CO-PAY'] = row.get('Copay Due')
            # classify insurance type using constants
            try:
                out['INSURANCE_TYPE'] = constants.classify_insurance(str(out.get('PRIMARY_INSURANCE') or ''))
            except Exception:
                out['INSURANCE_TYPE'] = None

            # Next appt parse
            next_date, provider = parse_next_appt(row.get('Next Appt Date and Provider'))
            out['NEXT_APPT_DATE'] = next_date
            # Use only the provider parsed from `Next Appt Date and Provider` and format as 'First Last'.
            # If not present, keep empty string.
            out['PROVIDER_NAME'] = format_provider_person(provider) or ''
            # keep clinic facility value but strip trailing bracketed numeric IDs like "[2130010001]"
            raw_cf = row.get('CLINIC FACILITY') or row.get('Clinic Facility') or row.get('Dept/Loc')
            if pd.notna(raw_cf) and str(raw_cf).strip():
                cf = str(raw_cf).strip()
                # remove trailing bracketed numeric id
                cf = re.sub(r"\s*\[\s*\d+\s*\]\s*$", "", cf)
                out['CLINIC_FACILITY'] = cf
            else:
                out['CLINIC_FACILITY'] = None

            # STATE: prefer explicit state columns, otherwise default to 'MI' for HFCC/ROSEVILLE clinics
            state_val = None
            for sc in ('State', 'STATE', 'Pt State', 'State/Province'):
                if sc in row and pd.notna(row.get(sc)) and str(row.get(sc)).strip():
                    state_val = str(row.get(sc)).strip()
                    break
            if not state_val:
                raw_cf_text = str(raw_cf or '').strip()
                if re.search(r"\b(HFCC|ROSEVILLE|CLINTON|MACOMB|MT CLEMENS|CHESTERFIELD)\b", raw_cf_text, re.IGNORECASE):
                    state_val = 'MI'
            out['STATE'] = state_val
            out['LAST_SEEN_DATE'] = row.get('Last Visit Date')

            # disease matches for this row (use precomputed matches + problem-list mapping + synonyms)
            row_matches = row['_disease_matches']
            # consult problem->cause map from constants for tokens
            pl_tokens = split_tokens(row.get('Problem List', ''))
            for t in pl_tokens:
                tok_key = str(t).strip().lower()
                # first consult explicit mapping
                if tok_key in constants.PROBLEM_TO_ICD and constants.PROBLEM_TO_ICD[tok_key].get('cause'):
                    row_matches.append({'cause': constants.PROBLEM_TO_ICD[tok_key]['cause'], 'icd': constants.PROBLEM_TO_ICD[tok_key]['icd'], 'token': t, 'is_primary': ('primary' in tok_key), 'is_secondary': ('secondary' in tok_key)})
                else:
                    # try synonyms
                    for syn, cause_name in constants.SYNONYM_TO_CAUSE.items():
                        if syn in tok_key:
                            row_matches.append({'cause': cause_name, 'icd': '', 'token': t, 'is_primary': ('primary' in tok_key), 'is_secondary': ('secondary' in tok_key)})
                            break
            # determine primary/secondary per rules using severity
            primary = None
            secondary = None
            severity_map = load_severity_map(CAUSE_SEVERITY)
            # A: token-level explicit labels
            for m in row_matches:
                if m.get('is_primary'):
                    primary = m['cause']
                    break
            for m in row_matches:
                if m.get('is_secondary') and m['cause'] != primary:
                    secondary = m['cause']
                    break
            # B: if no explicit primary, choose highest-severity matched cause
            if not primary and row_matches:
                uniq = {}
                for m in row_matches:
                        c = str(m.get('cause', '')).strip()
                        if c not in uniq:
                            uniq[c] = severity_map.get(c.lower(), 0)
                sorted_causes = sorted(uniq.items(), key=lambda x: x[1], reverse=True)
                if sorted_causes:
                    primary = sorted_causes[0][0]
                    if len(sorted_causes) > 1:
                        secondary = sorted_causes[1][0]
            # C: cross-row duplicates fallback for secondary if still empty
            if not secondary and distinct_causes:
                for c in distinct_causes:
                    if c != primary:
                        secondary = c
                        break

            out['PRIMARY_DX'] = primary
            out['SECONDARY_DX'] = secondary

            # set boolean disease flags
            # mapping from cause names (lower) to template columns
            cause_to_flag = {
                'coronary artery disease': 'CORONARY_ARTERY_DISEASE',
                'arrhythmia': 'ARRHYTHMIA',
                'chf (congestive heart failure)': 'CONGESTIVE_HEART_FAILURE',
                'peripheral vascular disease': 'PERIPHERAL_VASCULAR',
                'valvular heart disease': 'VALVULAR_HEART',
                'cerebrovascular accident': 'CERBOVASCULAR_ACCIDENT',
                'hyperlipidemia': 'HYPERLIPIDEMIA',
                'angina pectoris': 'ANGINA_PECTORIS',
                'hypotension': 'HYPOTENSION',
                'hypertension or pre hypertensive': 'HYPERTENSION',
                'obesity': 'OBESITY',
                'type 2 diabetes': 'DIABETES',
                'chronic kidney': 'CHRONIC_KIDNEY_DISEASE',
                'copd': 'COPD',
                'respiratory failure': 'RESPIRATORY_FAILURE',
                'asthma': 'ASTHMA',
                'sleep apnea': 'SLEEP_APNEA',
                'dyspnea': 'DYSPNEA',
                'emphysema': 'EMPHYSEMA',
                'bronchiectasis': 'BRONCHIECTASIS',
                'hypoxemia': 'HYPOXEMIA'
            }
            # initialize flags to 'NO' by default
            for flag in cause_to_flag.values():
                if flag in out:
                    out[flag] = 'NO'
            # set YES when matched in this row
            for m in row_matches:
                cn = str(m.get('cause', '')).strip().lower()
                if cn in cause_to_flag:
                    flag = cause_to_flag[cn]
                    out[flag] = 'YES'

            out_rows.append(out)
            # add timestamp to output filename
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            OUTPUT_XLSX = os.path.join(OUTPUT_DIR, f"consolidated_filled_{ts}.xlsx")

            out_df = pd.DataFrame(out_rows, columns=template_cols)
    # write to excel using template headers
    with pd.ExcelWriter(OUTPUT_XLSX, engine='openpyxl') as writer:
        out_df.to_excel(writer, index=False, sheet_name='Sheet1')

    print(f'Wrote consolidated file to: {OUTPUT_XLSX}')


if __name__ == '__main__':
    main()
