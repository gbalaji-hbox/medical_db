import pandas as pd

# Load patient demographics
demo_path = r'd:\Work_Folder\medical_db\src\HCT\patient-demographic.xlsx'
demo_df = pd.read_excel(demo_path, header=None)

# Find header row
header_row = None
for i, row in demo_df.iterrows():
    if row[1] == 'Pat Name':
        header_row = i
        break

demo_df.columns = demo_df.iloc[header_row]
demo_df = demo_df[header_row + 1:].reset_index(drop=True)
demo_df = demo_df.dropna(how='all')

# Load cleaned insurance
ins_path = r'd:\Work_Folder\medical_db\src\HCT\patient-insurance-cleaned.xlsx'
ins_df = pd.read_excel(ins_path)

# Group insurance by patient name
ins_grouped = ins_df.groupby('Name')

# Prepare output columns
output_columns = list(demo_df.columns) + [
    'Primary Insurance Name', 'Primary Insurance Number', 'Primary Group',
    'Secondary Insurance Name', 'Secondary Insurance Number',
    'Tertiary Insurance Name', 'Tertiary Insurance Number',
    'Copay (Primary)'
]

output_data = []

for _, demo_row in demo_df.iterrows():
    pat_name = demo_row['Pat Name']
    row_data = list(demo_row)

    # Initialize insurance fields
    primary_name = ''
    primary_num = ''
    primary_group = ''
    secondary_name = ''
    secondary_num = ''
    tertiary_name = ''
    tertiary_num = ''
    copay = ''

    if pat_name in ins_grouped.groups:
        patient_ins = ins_grouped.get_group(pat_name)

        # Primary (Enc Cob == 1)
        primary = patient_ins[patient_ins['Enc Cob'] == 1]
        if not primary.empty:
            primary_name = primary.iloc[0]['Ins Name']
            primary_num = primary.iloc[0]['Pol Nbr']
            primary_group = primary.iloc[0]['Group Name']
            copay = primary.iloc[0]['Co Amt']

        # Secondary (Enc Cob == 2)
        secondary = patient_ins[patient_ins['Enc Cob'] == 2]
        if not secondary.empty:
            secondary_name = secondary.iloc[0]['Ins Name']
            secondary_num = secondary.iloc[0]['Pol Nbr']

        # Tertiary (Enc Cob == 3)
        tertiary = patient_ins[patient_ins['Enc Cob'] == 3]
        if not tertiary.empty:
            tertiary_name = tertiary.iloc[0]['Ins Name']
            tertiary_num = tertiary.iloc[0]['Pol Nbr']

    row_data.extend([
        primary_name, primary_num, primary_group,
        secondary_name, secondary_num,
        tertiary_name, tertiary_num,
        copay
    ])

    output_data.append(row_data)

# Create output DataFrame
output_df = pd.DataFrame(output_data, columns=output_columns)

# Save to Excel
output_path = r'd:\Work_Folder\medical_db\src\HCT\patient-demographics-with-insurance.xlsx'
output_df.to_excel(output_path, index=False)

print(f"Output file created: {output_path}")
print(f"Total patients processed: {len(output_df)}")