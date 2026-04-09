#!/usr/bin/env python3
"""
HCT Medical Database Processing Pipeline

Processes patient demographic and insurance data into the consolidated template.
Fills available columns from raw data files, leaving comorbidities and diagnosis empty.

Usage: python main.py
"""

import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import openpyxl

def parse_patient_name(full_name: str) -> tuple[str, str, str, str]:
    """Parse 'Lastname, Firstname' into components."""
    if not full_name:
        return '', '', '', ''
    full_name = full_name.strip()
    if ',' not in full_name:
        # Assume single word is first name
        return full_name, '', '', full_name
    last_name, first_part = full_name.split(',', 1)
    last_name = last_name.strip()
    first_part = first_part.strip()

    # Split first part into first and middle names
    name_parts = first_part.split()
    first_name = name_parts[0] if name_parts else ''
    middle_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

    return first_name, middle_name, last_name, full_name

# Define paths
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR
TEMPLATE_DIR = BASE_DIR / "template"
CLEANED_DIR = BASE_DIR / "cleaned"
OUTPUT_DIR = BASE_DIR / "output"

def load_and_clean_demographics():
    """Load and clean patient demographics data"""
    cleaned_path = CLEANED_DIR / "patient-demographic-cleaned.xlsx"
    if cleaned_path.exists():
        print("Using existing cleaned demographics...")
        return pd.read_excel(cleaned_path)

    demo_path = RAW_DIR / "patient-demographic.xlsx"
    df = pd.read_excel(demo_path, header=None)

    # Find header row
    header_row = None
    for i, row in df.iterrows():
        if row[1] == 'Pat Name':
            header_row = i
            break

    df.columns = df.iloc[header_row]
    df = df[header_row + 1:].reset_index(drop=True)
    df = df.dropna(how='all')

    # Save cleaned
    df.to_excel(cleaned_path, index=False)

    return df

def load_and_clean_insurance():
    """Load and clean patient insurance data"""
    cleaned_path = CLEANED_DIR / "patient-insurance-cleaned.xlsx"
    if cleaned_path.exists():
        print("Using existing cleaned insurance...")
        return pd.read_excel(cleaned_path)

    ins_path = RAW_DIR / "patient-insurance.xlsx"
    df = pd.read_excel(ins_path, header=None)

    # Find header row
    header_row = None
    for i, row in df.iterrows():
        if row[2] == 'Name':
            header_row = i
            break

    df.columns = df.iloc[header_row]
    df = df[header_row + 1:].reset_index(drop=True)
    df = df.dropna(how='all')

    # Remove duplicates
    df = df.drop_duplicates().reset_index(drop=True)

    # Assign insurance names based on provider rows
    df['insurance_name'] = ''
    current_provider = ''
    for idx in df.index:
        row = df.loc[idx]
        name = row['Name']
        payor_value = str(df.iloc[idx, 1]).strip()  # Column 1 has payor name
        if pd.isna(name) or name.strip() == '':
            # Provider row
            if payor_value and payor_value != 'nan':
                current_provider = payor_value
        else:
            # Patient row
            df.at[idx, 'insurance_name'] = current_provider

    # Save cleaned
    df.to_excel(cleaned_path, index=False)

    return df

def merge_data(demo_df, ins_df):
    """Merge demographics with insurance data using Name + DOB as unique identifier"""
    # Create unique keys, handling NaN
    demo_df['merge_key'] = demo_df['Pat Name'].fillna('') + '_' + demo_df['Birth Dt'].fillna('').astype(str)
    ins_df['merge_key'] = ins_df['Name'].fillna('') + '_' + ins_df['Birth Dt'].fillna('').astype(str)

    # Group insurance by merge key
    ins_grouped = ins_df.groupby('merge_key')

    merged_data = []

    for _, demo_row in demo_df.iterrows():
        merge_key = demo_row['merge_key']
        pat_name = demo_row['Pat Name']
        if pd.isna(pat_name) or str(pat_name).strip() == '':
            continue  # Skip empty rows

        row = demo_row.drop('merge_key').to_dict()

        # Parse name
        first_name, middle_name, last_name, full_name = parse_patient_name(str(pat_name))
        row['first_name'] = first_name
        row['middle_name'] = middle_name
        row['last_name'] = last_name
        row['full_name'] = full_name

        # Initialize insurance fields
        insurance_info = {
            'primary_insurance': '',
            'primary_id': '',
            'primary_group': '',
            'secondary_insurance': '',
            'secondary_id': '',
            'secondary_group': '',
            'tertiary_insurance': '',
            'tertiary_id': '',
            'tertiary_group': '',
            'insurance_type': '',
            'co_pay': ''
        }

        if merge_key in ins_grouped.groups:
            patient_ins = ins_grouped.get_group(merge_key)

            # Primary
            primary = patient_ins[patient_ins['Enc Cob'] == 1]
            if not primary.empty:
                insurance_info['primary_insurance'] = primary.iloc[0]['insurance_name']
                insurance_info['primary_id'] = primary.iloc[0]['Pol Nbr']
                insurance_info['primary_group'] = primary.iloc[0]['Group Name']
                insurance_info['insurance_type'] = primary.iloc[0]['Ins Type']
                insurance_info['co_pay'] = primary.iloc[0]['Co Amt']

            # Secondary
            secondary = patient_ins[patient_ins['Enc Cob'] == 2]
            if not secondary.empty:
                insurance_info['secondary_insurance'] = secondary.iloc[0]['insurance_name']
                insurance_info['secondary_id'] = secondary.iloc[0]['Pol Nbr']
                insurance_info['secondary_group'] = secondary.iloc[0]['Group Name']

            # Tertiary
            tertiary = patient_ins[patient_ins['Enc Cob'] == 3]
            if not tertiary.empty:
                insurance_info['tertiary_insurance'] = tertiary.iloc[0]['insurance_name']
                insurance_info['tertiary_id'] = tertiary.iloc[0]['Pol Nbr']
                insurance_info['tertiary_group'] = tertiary.iloc[0]['Group Name']

        row.update(insurance_info)
        merged_data.append(row)

    merged_df = pd.DataFrame(merged_data)

    # Filter to keep only patients with at least primary insurance
    merged_df = merged_df[merged_df['primary_insurance'].notna() & (merged_df['primary_insurance'] != '')]

    # Remove duplicates based on Md Rc, keeping first occurrence
    merged_df = merged_df.drop_duplicates(subset=['Md Rc'], keep='first')

    return merged_df

def fill_template(merged_df):
    """Fill the consolidated template with merged data"""
    template_path = TEMPLATE_DIR / "consolidated_view-template - new.xlsx"
    template_df = pd.read_excel(template_path)

    # Create mapping from merged data to template columns
    column_mapping = {
        'EMR ID': 'Md Rc',  # Medical Record number
        'PATIENT EMR NAME': 'Pat Name',
        'FIRST NAME': 'first_name',
        'MIDDLE NAME': 'middle_name',
        'LAST NAME': 'last_name',
        'PATIENT FULL NAME': '',
        'DATE OF BIRTH': 'Birth Dt',
        'GENDER': 'Sex Code',
        'STREET ADDRESS': 'Addr 1',
        'CITY': 'City',
        'STATE': 'State',
        'ZIP': 'Zip',
        'HOME PHONE': 'Hm Phone',
        'MOBILE PHONE': 'Cell Phone',
        'WORK PHONE': 'Day Phone',
        'EMAIL ADDRESS': 'Email Addr',
        'LANGUAGE': 'Preferred Language',
        'RACE': 'Race',
        'EMERGENCY CONTACT NAME': 'Guar Name',
        'EMERGENCY RELATIONSHIP': 'Pat/Guar Rel',
        'EMERGENCY CONTACT HOME PHONE': 'Sec Hm Phone',
        'EMERGENCY CONTACT MOBILE PHONE': '',  # Not directly available
        'MEDICARE ID': '',  # Not available
        'PRIMARY INSURANCE': 'primary_insurance',
        'PRIMARY ID': 'primary_id',
        'PRIMARY GROUP': 'primary_group',
        'SECONDARY INSURANCE': 'secondary_insurance',
        'SECONDARY ID': 'secondary_id',
        'SECONDARY GROUP': 'secondary_group',
        'TERITARY INSURANCE': 'tertiary_insurance',
        'TERITARY ID': 'tertiary_id',
        'TERITARY GROUP': 'tertiary_group',
        'INSURANCE TYPE': 'insurance_type',
        'CO-PAY': 'co_pay',
        # Comorbidities - leave empty
        'CORONARY ARTERY DISEASE': '',
        'ARRHYTHMIA': '',
        'CONGESTIVE HEART FAILURE': '',
        'PERIPHERAL VASCULAR': '',
        'VALVULAR HEART': '',
        'CERBOVASCULAR ACCIDENT': '',
        'HYPERLIPIDEMIA': '',
        'ANGINA PECTORIS': '',
        'HYPOTENSION': '',
        'HYPERTENSION': '',
        'OBESITY': '',
        'DIABETES': '',
        'CHRONIC KIDNEY DISEASE': '',
        'COPD': '',
        'RESPIRATORY FAILURE': '',
        'ASTHMA': '',
        'SLEEP APNEA': '',
        'DYSPNEA': '',
        'EMPHYSEMA': '',
        'BRONCHIECTASIS': '',
        'HYPOXEMIA': '',
        'PRIMARY DX': '',
        'SECONDARY DX': '',
        'PRIMARY ICD': '',
        'SECONDARY ICD': '',
        'LAST SEEN DATE': 'Lst Enc Dt',
        'NEXT APPT': 'Nxt Appt Dt',
        'PROVIDER DATA': 'Provider Name',
        'PROVIDER NAME': 'Provider Name',
        'CLINIC FACILITY': '',  # Could be "Heart Center Of North Texas PA"
        'PRIMARY CARE PROVIDER': 'Prim Care Phys',
        'MEDICATIONS': '',
        'ENCOUNTER NOTES': ''
    }

    # Fill the template
    filled_data = []
    date_columns = ['DATE OF BIRTH', 'LAST SEEN DATE', 'NEXT APPT']
    emergency_columns = ['EMERGENCY CONTACT NAME', 'EMERGENCY RELATIONSHIP', 'EMERGENCY CONTACT HOME PHONE', 'EMERGENCY CONTACT MOBILE PHONE']
    
    for _, row in merged_df.iterrows():
        filled_row = {}
        for template_col, source_col in column_mapping.items():
            if template_col in emergency_columns:
                filled_row[template_col] = ''
            elif template_col == 'CLINIC FACILITY':
                filled_row[template_col] = 'Heart Center Of North Texas PA'
            elif template_col == 'PROVIDER NAME':
                if source_col and source_col in row:
                    name = row[source_col]
                    if pd.notna(name) and isinstance(name, str) and ',' in name:
                        last, first = name.split(',', 1)
                        filled_row[template_col] = f"{first.strip()} {last.strip()}"
                    else:
                        filled_row[template_col] = name
                else:
                    filled_row[template_col] = ''
            elif template_col == 'PATIENT FULL NAME':
                first = row.get('first_name', '')
                middle = row.get('middle_name', '')
                last = row.get('last_name', '')
                if pd.notna(middle) and str(middle).strip():
                    full = f"{first} {middle} {last}".strip()
                else:
                    full = f"{first} {last}".strip()
                filled_row[template_col] = full
            elif template_col == 'GENDER':
                if source_col and source_col in row:
                    gender = row[source_col]
                    if pd.notna(gender):
                        g = str(gender).strip().upper()
                        if g == 'M':
                            filled_row[template_col] = 'Male'
                        elif g == 'F':
                            filled_row[template_col] = 'Female'
                        else:
                            filled_row[template_col] = gender
                    else:
                        filled_row[template_col] = gender
                else:
                    filled_row[template_col] = ''
            elif source_col and source_col in row:
                value = row[source_col]
                if template_col in date_columns and pd.notna(value):
                    if isinstance(value, str) and value.strip():
                        try:
                            # Try to parse common date formats
                            dt = pd.to_datetime(value, errors='coerce')
                            if pd.notna(dt):
                                filled_row[template_col] = dt.to_pydatetime()
                            else:
                                filled_row[template_col] = value
                        except:
                            filled_row[template_col] = value
                    elif isinstance(value, (pd.Timestamp, datetime)):
                        filled_row[template_col] = value
                    else:
                        filled_row[template_col] = value
                else:
                    filled_row[template_col] = value
            else:
                filled_row[template_col] = ''
        filled_data.append(filled_row)

    filled_df = pd.DataFrame(filled_data)

    # Ensure date columns are datetime type for proper Excel date formatting
    for col in date_columns:
        if col in filled_df.columns:
            filled_df[col] = pd.to_datetime(filled_df[col], errors='coerce')

    # Generate timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"HCT_consolidated_{timestamp}.xlsx"
    output_path = OUTPUT_DIR / output_filename

    filled_df.to_excel(output_path, index=False)

    # Format date columns in Excel to mm-dd-yyyy
    wb = openpyxl.load_workbook(output_path)
    ws = wb.active
    for i, col in enumerate(filled_df.columns):
        if col in date_columns:
            col_letter = openpyxl.utils.get_column_letter(i + 1)
            for row in range(2, ws.max_row + 1):  # Skip header row
                cell = ws[f'{col_letter}{row}']
                if cell.value:
                    cell.number_format = 'mm-dd-yyyy'
    wb.save(output_path)

    return output_path

def main():
    print("Starting HCT data processing...")

    # Create directories if not exist
    CLEANED_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Load and clean data
    print("Loading and cleaning demographics...")
    demo_df = load_and_clean_demographics()

    print("Loading and cleaning insurance...")
    ins_df = load_and_clean_insurance()

    # Merge data
    print("Merging data...")
    merged_df = merge_data(demo_df, ins_df)

    # Fill template
    print("Filling template...")
    output_path = fill_template(merged_df)

    print(f"Processing complete! Output saved to: {output_path}")
    print(f"Total patients processed: {len(merged_df)}")

if __name__ == "__main__":
    main()