import pandas as pd, os, re
ROOT = r'D:\Work_Folder\medical_db'
TEMPLATE = os.path.join(ROOT,'src','CIM','template','consolidated_view-template.xlsx')
HBOX = os.path.join(ROOT,'src','CIM','Final_Hbox_3_19_26.xlsx')
CIM_MAP = os.path.join(ROOT,'src','CIM','mappings','column_mapping.csv')
CAM_MAP = os.path.join(ROOT,'src','CAM','mappings','column_mapping_data_new.csv')
CLINIC_FIELDS = os.path.join(ROOT,'src','CIM','template','Clinic DB Fields (1).xlsx')
OUT = os.path.join(ROOT,'src','CIM','mappings','column_mapping_generated.csv')

def normalize(s):
    if pd.isna(s):
        return ''
    return re.sub(r'[^A-Za-z0-9]', '', str(s).strip()).lower()

# load
tpl = pd.read_excel(TEMPLATE, sheet_name=0, nrows=0, engine='openpyxl')
template_cols = [c for c in tpl.columns]

h = pd.read_excel(HBOX, sheet_name='Sheet1', engine='openpyxl')
hbox_cols = [c for c in h.columns if isinstance(c,str)]

cim_map = pd.read_csv(CIM_MAP)
cam_map = pd.read_csv(CAM_MAP)

# clinic fields extraction names
cf = pd.read_excel(CLINIC_FIELDS, sheet_name=0, engine='openpyxl', header=0)
# try to find a column that contains 'Extraction' in its name (case-insensitive)
extraction_col = None
for col in cf.columns:
    if isinstance(col, str) and 'extraction' in col.lower():
        extraction_col = col
        break
if extraction_col is None:
    # fallback: try common names
    for col in cf.columns:
        if isinstance(col, str) and any(x in col.lower() for x in ['field', 'extraction fields', 'extraction']):
            extraction_col = col
            break
if extraction_col is None:
    # as a last resort, take the third column if present
    if len(cf.columns) >= 3:
        extraction_col = cf.columns[2]
    else:
        extraction_col = None

if extraction_col is None:
    clinic_field_names = []
else:
    clinic_field_names = [str(x).strip() for x in cf[extraction_col].dropna().tolist()]

# build normalized lookup
hbox_norm = {normalize(c): c for c in hbox_cols}
clinic_norm = {normalize(c): c for c in clinic_field_names}
cam_suggest = {row['template_column']: row['suggested_data_column'] for _, row in cam_map.iterrows() if pd.notna(row['suggested_data_column']) and str(row['suggested_data_column']).strip()}

out_rows = []
for tpl_col in template_cols:
    best_sources = []
    notes = []
    # 1) check existing CIM mapping
    cim_row = cim_map[cim_map['template_column'] == tpl_col]
    if not cim_row.empty:
        src = str(cim_row.iloc[0]['hbox_source'])
        if src and src.upper() != 'NOT MATCHED':
            # expand semicolon
            parts = [p.strip() for p in src.split(';') if p.strip()]
            for p in parts:
                best_sources.append(p)
    # 2) check CAM suggestion
    cam_s = cam_suggest.get(tpl_col)
    if cam_s and cam_s not in best_sources:
        best_sources.append(cam_s)
    # 3) try exact match with HBOX
    if not best_sources:
        if tpl_col in hbox_cols:
            best_sources.append(tpl_col)
    # 4) normalized match
    if not best_sources:
        n = normalize(tpl_col)
        if n in hbox_norm:
            best_sources.append(hbox_norm[n]); notes.append('normalized match to HBOX')
        elif n in clinic_norm:
            best_sources.append(clinic_norm[n]); notes.append('normalized match to Clinic Fields')
    # 5) try partial substring matches from clinic fields
    if not best_sources:
        for cfname in clinic_field_names:
            if normalize(cfname).startswith(n[:4]) and cfname not in best_sources:
                best_sources.append(cfname); notes.append('clinic fields prefix match')
    # set confidence
    if not best_sources:
        confidence = 'low'
        best = ''
    else:
        confidence = 'high' if any(s in hbox_cols for s in best_sources) else 'medium'
        best = '; '.join(best_sources)
    out_rows.append({'template_column': tpl_col, 'suggested_hbox_sources': best, 'confidence': confidence, 'notes': '; '.join(notes)})

out_df = pd.DataFrame(out_rows)
out_df.to_csv(OUT, index=False)
print('Wrote mapping to', OUT)
