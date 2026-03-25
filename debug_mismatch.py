import pandas as pd
from pathlib import Path

# Read the output Excel file
output_file = Path('src/MCA/output/MCA_consolidated_235321.xlsx')
df = pd.read_excel(output_file)

print('=== INVESTIGATING PRIMARY ICD vs COMORBIDITY MISMATCH ===')
print(f'Total records: {len(df)}')
print()

# Define comorbidity columns
comorbidity_cols = [
    'CORONARY ARTERY DISEASE', 'ARRHYTHMIA', 'CONGESTIVE HEART FAILURE', 'PERIPHERAL VASCULAR',
    'VALVULAR HEART', 'CEREBROVASCULAR ACCIDENT', 'HYPERLIPIDEMIA', 'ANGINA PECTORIS',
    'HYPOTENSION', 'HYPERTENSION', 'OBESITY', 'DIABETES', 'CHRONIC KIDNEY DISEASE',
    'COPD', 'RESPIRATORY FAILURE', 'ASTHMA', 'SLEEP APNEA', 'DYSPNEA', 'EMPHYSEMA',
    'BRONCHIECTASIS', 'HYPOXEMIA'
]

# Create a column to check if any comorbidity is YES
df['any_comorbidity_yes'] = df[comorbidity_cols].eq('YES').any(axis=1)

# Check PRIMARY ICD populated
primary_icd_populated = df['PRIMARY ICD'].notna()
print(f'PRIMARY ICD populated: {primary_icd_populated.sum()}')
print(f'Any comorbidity YES: {df["any_comorbidity_yes"].sum()}')
print()

# Find mismatches
icd_but_no_comorbidity = df[primary_icd_populated & ~df['any_comorbidity_yes']]
comorbidity_but_no_icd = df[~primary_icd_populated & df['any_comorbidity_yes']]

print(f'Records with PRIMARY ICD but no comorbidity YES: {len(icd_but_no_comorbidity)}')
print(f'Records with comorbidity YES but no PRIMARY ICD: {len(comorbidity_but_no_icd)}')
print()

if len(icd_but_no_comorbidity) > 0:
    print('=== RECORDS WITH PRIMARY ICD BUT NO COMORBIDITY YES ===')
    for idx, row in icd_but_no_comorbidity.head(5).iterrows():
        print(f'Row {idx}: PRIMARY ICD="{row["PRIMARY ICD"]}", PRIMARY DX="{row["PRIMARY DX"]}"')
        # Check which comorbidities are set
        yes_comorbidities = [col for col in comorbidity_cols if row[col] == 'YES']
        print(f'  Comorbidities set to YES: {yes_comorbidities}')
    print()

if len(comorbidity_but_no_icd) > 0:
    print('=== RECORDS WITH COMORBIDITY YES BUT NO PRIMARY ICD ===')
    for idx, row in comorbidity_but_no_icd.head(5).iterrows():
        print(f'Row {idx}: PRIMARY ICD="{row["PRIMARY ICD"]}", PRIMARY DX="{row["PRIMARY DX"]}"')
        # Check which comorbidities are set
        yes_comorbidities = [col for col in comorbidity_cols if row[col] == 'YES']
        print(f'  Comorbidities set to YES: {yes_comorbidities}')
    print()

# Check what causes are in PRIMARY DX for the mismatch cases
if len(icd_but_no_comorbidity) > 0:
    print('=== PRIMARY DX VALUES FOR ICD-BUT-NO-COMORBIDITY CASES ===')
    primary_dx_values = icd_but_no_comorbidity['PRIMARY DX'].value_counts()
    print(primary_dx_values.head(10))
    print()

# Load the API mapping to understand what should be mapped
api_df = pd.read_csv('src/CIM/disease/api_prescriptioncauselist_202603101243.csv')
cause_mapping = dict(zip(api_df['icd_code'], api_df['cause']))
print('=== API CAUSE MAPPING (first 10) ===')
for i, (icd, cause) in enumerate(list(cause_mapping.items())[:10]):
    print(f'{icd}: {cause}')
print('...')