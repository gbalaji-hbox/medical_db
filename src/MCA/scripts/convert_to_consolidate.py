#!/usr/bin/env python3
"""
Medical Database Template Formatter

Transforms the consolidated CSV to match the template format with:
- Patient name parsing (First/Middle/Last Name)
- Diagnosis to comorbidity mapping
- Insurance type classification
- Provider name parsing
- Missing column additions
"""

import os
import csv
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import openpyxl

# Insurance type classification constants (copied from CIM/constants.py for independence)
INSURANCE_TYPE_MAP = [
    (['medicare advantage', 'med adv', 'med adv', 'medicareadvantage', 'medicare adv', 'medicare plus'], 'medicare advantage'),
    (['medicare part', 'medicare/medicare', 'medicare rail', 'medicare'], 'medicare'),
    (['medicaid', 'health link', 'mi health link', 'healthy mi', 'medicaid hmo'], 'medicaid'),
    (['dual', 'd-snp', 'duals', 'dual complete', 'd-snp', 'snp'], 'medicare advantage'),
    (['advantage', 'med adv', 'med adv ppo', 'med adv hmo', 'med adv ppo'], 'medicare advantage'),
    (['hap', 'blue', 'blue cross', 'blue care', 'bcn', 'aetna', 'cigna', 'humana', 'priority health', 'united', 'molina', 'meridian', 'wellcare', 'geha', 'align', 'aco', 'ascension', 'trinity', 'mcclaren', 'gravie', 'meritain', 'umr', 'pa i', 'pai', 'cofinity', 'cofinity', 'core', 'core', 'mutual of omaha', 'etna'], 'commercial'),
    (['self pay', 'self-pay', 'selfpay'], 'self pay'),
    (['workers compensation', 'wc ', 'wc '], 'workers comp'),
    (['motor vehicle', 'auto '], 'auto'),
    (['veterans', 'va', 'triwest', 'veterans administration', 'optum va'], 'veterans'),
    (['tricare'], 'government'),
]


def classify_insurance(ins_text: str) -> str:
    """Classify insurance type based on observed Primary Cvg/Primary Payer values."""
    if not ins_text or not str(ins_text).strip():
        return ''
    s = str(ins_text).lower()
    for patterns, label in INSURANCE_TYPE_MAP:
        for p in patterns:
            if p and p in s:
                return label
    return 'other'


class TemplateFormatter:
    """Class to format consolidated data to match template structure."""

    def __init__(self, input_csv: str, output_excel: str):
        self.input_csv = input_csv
        self.output_excel = output_excel

        # Load ICD to cause mapping
        self.cause_mapping = self._load_cause_mapping()

        # Template column order
        self.template_columns = [
            'EMR ID', 'PATIENT EMR NAME', 'FIRST NAME', 'MIDDLE NAME', 'LAST NAME',
            'PATIENT FULL NAME', 'DATE OF BIRTH', 'GENDER', 'STREET ADDRESS', 'CITY',
            'STATE', 'ZIP', 'HOME PHONE', 'MOBILE PHONE', 'WORK PHONE', 'EMAIL ADDRESS',
            'LANGUAGE', 'RACE', 'EMERGENCY CONTACT NAME', 'EMERGENCY RELATIONSHIP',
            'EMERGENCY CONTACT HOME PHONE', 'EMERGENCY CONTACT MOBILE PHONE', 'MEDICARE ID',
            'PRIMARY INSURANCE', 'PRIMARY ID', 'PRIMARY GROUP', 'SECONDARY INSURANCE',
            'SECONDARY ID', 'SECONDARY GROUP', 'TERITARY INSURANCE', 'TERITARY ID',
            'TERITARY GROUP', 'INSURANCE TYPE', 'CO-PAY',
            # Comorbidities
            'CORONARY ARTERY DISEASE', 'ARRHYTHMIA', 'CONGESTIVE HEART FAILURE',
            'PERIPHERAL VASCULAR', 'VALVULAR HEART', 'CEREBROVASCULAR ACCIDENT',
            'HYPERLIPIDEMIA', 'ANGINA PECTORIS', 'HYPOTENSION', 'HYPERTENSION',
            'OBESITY', 'DIABETES', 'CHRONIC KIDNEY DISEASE', 'COPD',
            'RESPIRATORY FAILURE', 'ASTHMA', 'SLEEP APNEA', 'DYSPNEA',
            'EMPHYSEMA', 'BRONCHIECTASIS', 'HYPOXEMIA',
            # Diagnosis fields
            'PRIMARY DX', 'SECONDARY DX', 'PRIMARY ICD', 'SECONDARY ICD',
            'LAST SEEN DATE', 'NEXT APPT', 'PROVIDER DATA', 'PROVIDER NAME',
            'CLINIC FACILITY', 'PRIMARY CARE PROVIDER', 'MEDICATIONS', 'ENCOUNTER NOTES'
        ]

    def _load_cause_mapping(self) -> Dict[str, str]:
        """Load cause to ICD mapping from api_prescriptioncauselist.csv."""
        cause_file = Path(__file__).parent.parent / 'template' / 'api_prescriptioncauselist_202603101243.csv'
        cause_df = pd.read_csv(cause_file)
        # Create mapping from ICD code to cause name
        icd_to_cause = dict(zip(cause_df['icd_code'], cause_df['cause']))
        return icd_to_cause

    def _parse_patient_name(self, full_name: str) -> Tuple[str, str, str, str]:
        """Parse 'Lastname, Firstname' into components."""
        if not full_name or ',' not in full_name:
            return full_name, '', '', '', full_name

        last_name, first_part = full_name.split(',', 1)
        last_name = last_name.strip()
        first_part = first_part.strip()

        # Split first part into first and middle names
        name_parts = first_part.split()
        first_name = name_parts[0] if name_parts else ''
        middle_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        # Create full name as First Middle Last
        full_name_formatted = f"{first_name} {middle_name} {last_name}".strip()

        return last_name, first_name, middle_name, full_name_formatted

    def _parse_date(self, date_str: str) -> Optional[pd.Timestamp]:
        """Parse date string from various inconsistent formats and normalize to proper datetime for Excel date formatting."""
        if not date_str or pd.isna(date_str) or str(date_str).strip() == '':
            return None
        
        try:
            # Clean the date string and normalize separators
            date_clean = str(date_str).strip()
            
            # Replace all separators with '/' for consistency
            date_clean = date_clean.replace('-', '/').replace('.', '/').replace('\\', '/')
            
            # Split into parts
            parts = date_clean.split('/')
            if len(parts) != 3:
                # If not 3 parts, try automatic parsing
                return pd.to_datetime(date_clean)
            
            # Parse month, day, year - handle single digit values
            try:
                month = int(parts[0])
                day = int(parts[1]) 
                year = int(parts[2])
                
                # Handle 2-digit years
                if year < 100:
                    if year > 50:  # Assume 1950s-1999
                        year += 1900
                    else:  # Assume 2000s
                        year += 2000
                
                # Validate ranges
                if not (1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2100):
                    raise ValueError("Invalid date range")
                
                # Create datetime
                return pd.Timestamp(year=year, month=month, day=day)
                
            except (ValueError, IndexError):
                # If manual parsing fails, try pandas automatic parsing
                return pd.to_datetime(date_clean)
            
        except (ValueError, TypeError):
            # If parsing fails, return None (will be empty in Excel)
            return None

    def _parse_provider_name(self, provider_data: str) -> str:
        """Parse provider name to 'Firstname Lastname' format, stripping degrees."""
        if not provider_data:
            return ''

        # Common medical degrees to strip
        degrees = ['D.O.', 'M.D.', 'DO', 'MD', 'NP', 'PA', 'RN', 'DNP', 'FNP']

        parts = [p.strip() for p in provider_data.split(',')]

        if len(parts) == 2:
            # Format: "Lastname Degree, Firstname" or "Lastname, Firstname"
            last_part = parts[0]
            first_name = parts[1]

            # Strip degree from last name if present
            last_name = last_part
            for degree in degrees:
                if last_name.upper().endswith(degree.upper()):
                    last_name = last_name[:-len(degree)].strip()
                    break

            return f"{first_name} {last_name}"

        elif len(parts) >= 3:
            # Format: "Lastname, Firstname, Degree"
            last_name = parts[0]
            first_name = parts[1]
            # Ignore the degree part (parts[2])

            return f"{first_name} {last_name}"

        # Fallback: return as-is if format not recognized
        return provider_data

    def _map_diagnosis_to_comorbidities(self, all_diagnoses: str, all_icds: str) -> Tuple[Dict[str, str], str, str, str, str]:
        """Map all diagnoses for a patient to comorbidity flags and return primary/secondary DX and ICD.

        Processes ALL diagnoses to set comprehensive comorbidity flags.
        Returns the first two matching diagnoses as Primary and Secondary.
        Only assigns comorbidity flags and DX when there's a clear match with the API prescription list.
        """
        comorbidities = {}
        primary_dx = ''
        primary_icd = ''
        secondary_dx = ''
        secondary_icd = ''

        # Initialize all comorbidities to 'NO'
        comorbidity_columns = [
            'CORONARY ARTERY DISEASE', 'ARRHYTHMIA', 'CONGESTIVE HEART FAILURE',
            'PERIPHERAL VASCULAR', 'VALVULAR HEART', 'CEREBROVASCULAR ACCIDENT',
            'HYPERLIPIDEMIA', 'ANGINA PECTORIS', 'HYPOTENSION', 'HYPERTENSION',
            'OBESITY', 'DIABETES', 'CHRONIC KIDNEY DISEASE', 'COPD',
            'RESPIRATORY FAILURE', 'ASTHMA', 'SLEEP APNEA', 'DYSPNEA',
            'EMPHYSEMA', 'BRONCHIECTASIS', 'HYPOXEMIA'
        ]

        for col in comorbidity_columns:
            comorbidities[col] = 'NO'

        # Split all diagnoses and ICDs
        diagnoses_list = [d.strip() for d in all_diagnoses.split('|') if d.strip()]
        icds_list = [i.strip() for i in all_icds.split('|') if i.strip()]
        
        # Pair diagnoses with their ICD codes
        diagnosis_pairs = list(zip(diagnoses_list, icds_list)) if len(diagnoses_list) == len(icds_list) else []
        
        matching_diagnoses = []  # Store (diagnosis, icd, cause) tuples for matches
        
        # Process each diagnosis-ICD pair
        for diagnosis, icd in diagnosis_pairs:
            if not icd:
                continue
                
            matched_cause = None

            # Try exact match first
            if icd in self.cause_mapping:
                matched_cause = self.cause_mapping[icd]
            else:
                # Try range matching with special diabetes handling
                diabetes_codes = ['E10', 'E11', 'E13']
                if any(icd.startswith(code) for code in diabetes_codes):
                    # Find the diabetes entry in the mapping
                    for mapped_icd, cause_name in self.cause_mapping.items():
                        if cause_name == 'Type 2 Diabetes':
                            matched_cause = cause_name
                            break
                else:
                    # Regular range matching for other conditions
                    for mapped_icd, cause_name in self.cause_mapping.items():
                        if icd.startswith(mapped_icd.split('.')[0]):
                            matched_cause = cause_name
                            break

            # If we found a match, add to matching diagnoses and set comorbidity
            if matched_cause:
                matching_diagnoses.append((diagnosis, icd, matched_cause))

                # Map cause name to comorbidity column and set to 'YES'
                cause_to_comorbidity = {
                    'Coronary Artery Disease': 'CORONARY ARTERY DISEASE',
                    'Arrhythmia': 'ARRHYTHMIA',
                    'CHF (Congestive Heart Failure)': 'CONGESTIVE HEART FAILURE',
                    'Peripheral Vascular Disease': 'PERIPHERAL VASCULAR',
                    'Valvular Heart Disease': 'VALVULAR HEART',
                    'Cerebrovascular Accident': 'CEREBROVASCULAR ACCIDENT',
                    'Hyperlipidemia': 'HYPERLIPIDEMIA',
                    'Angina Pectoris': 'ANGINA PECTORIS',
                    'Hypotension': 'HYPOTENSION',
                    'Hypertension': 'HYPERTENSION',
                    'Obesity': 'OBESITY',
                    'Type 2 Diabetes': 'DIABETES',
                    'Chronic Kidney': 'CHRONIC KIDNEY DISEASE',
                    'COPD': 'COPD',
                    'Chronic Bronchitis': 'COPD',  # Chronic Bronchitis maps to COPD
                    'Respiratory Failure': 'RESPIRATORY FAILURE',
                    'Asthma': 'ASTHMA',
                    'Sleep Apnea': 'SLEEP APNEA',
                    'Dyspnea': 'DYSPNEA',
                    'Emphysema': 'EMPHYSEMA',
                    'Emphysema ': 'EMPHYSEMA',  # Handle trailing space
                    'Bronchiectasis': 'BRONCHIECTASIS',
                    'Hypoxemia': 'HYPOXEMIA',
                    'Chronic Hypoxia': 'HYPOXEMIA'  # Map Chronic Hypoxia to HYPOXEMIA
                }

                if matched_cause in cause_to_comorbidity:
                    comorbidities[cause_to_comorbidity[matched_cause]] = 'YES'

        # Set Primary and Secondary DX/ICD from the first two matching diagnoses
        if len(matching_diagnoses) >= 1:
            primary_dx = matching_diagnoses[0][2]  # Use the cause name
            primary_icd = matching_diagnoses[0][1]  # Use the ICD code
            
        if len(matching_diagnoses) >= 2:
            secondary_dx = matching_diagnoses[1][2]  # Use the cause name  
            secondary_icd = matching_diagnoses[1][1]  # Use the ICD code

        return comorbidities, primary_dx, primary_icd, secondary_dx, secondary_icd

    def format_data(self) -> int:
        """Transform consolidated CSV to template format."""
        # Read input CSV
        df = pd.read_csv(self.input_csv)

        formatted_records = []

        for _, row in df.iterrows():
            # Parse patient name
            last_name, first_name, middle_name, full_name = self._parse_patient_name(str(row.get('patient_name', '')))

            # Skip test records - check for specific test names
            patient_name_lower = str(row.get('patient_name', '')).lower().strip()
            test_names = [
                'tester, randell', 'test, test', 'test,blanche', 'test, allison',
                'tester, testy', 'test,mickey', 'test, blanche', 'test, mickey'
            ]
            
            if patient_name_lower in test_names or last_name.lower().strip() == 'test':
                continue

            # Map diagnosis to comorbidities
            comorbidities, primary_dx, primary_icd, secondary_dx, secondary_icd = self._map_diagnosis_to_comorbidities(str(row.get('all_diagnoses', '')), str(row.get('all_icds', '')))

            # Classify insurance type
            insurance_type = classify_insurance(str(row.get('payer', '')))

            # Parse provider name - handle NaN/None values
            provider_data = row.get('provider_data')
            if pd.isna(provider_data) or not str(provider_data).strip():
                provider_name = ''
            else:
                provider_name = self._parse_provider_name(str(provider_data))

            # Process email - lowercase and trim spaces
            email = str(row.get('email', '')).strip().lower() if not pd.isna(row.get('email')) else ''

            # Parse dates for proper Excel date formatting
            dob_date = self._parse_date(str(row.get('dob', '')))
            last_seen_date = self._parse_date(str(row.get('last_visit', '')))
            next_appt_date = self._parse_date(str(row.get('next_appointment', '')))

            # Build formatted record
            record = {
                'EMR ID': row.get('patient_id', ''),
                'PATIENT EMR NAME': row.get('patient_name', ''),
                'FIRST NAME': first_name,
                'MIDDLE NAME': middle_name,
                'LAST NAME': last_name,
                'PATIENT FULL NAME': full_name,
                'DATE OF BIRTH': dob_date,
                'GENDER': row.get('sex', ''),
                'GENDER': row.get('sex', ''),
                'STREET ADDRESS': row.get('address', ''),
                'CITY': row.get('city', ''),
                'STATE': row.get('state', ''),
                'ZIP': row.get('zip', ''),
                'HOME PHONE': row.get('home_number', ''),
                'MOBILE PHONE': row.get('mobile_number', ''),
                'WORK PHONE': '',  # Not available
                'EMAIL ADDRESS': email,
                'LANGUAGE': 'English',
                'RACE': '',  # Not available
                'EMERGENCY CONTACT NAME': row.get('emergency_contact', ''),
                'EMERGENCY RELATIONSHIP': '',  # Not available
                'EMERGENCY CONTACT HOME PHONE': row.get('emergency_contact_number', ''),
                'EMERGENCY CONTACT MOBILE PHONE': '',  # Not available
                'MEDICARE ID': '',  # Not available
                'PRIMARY INSURANCE': row.get('payer_name_p', ''),
                'PRIMARY ID': row.get('member_id_p', ''),
                'PRIMARY GROUP': '',  # Leave blank as requested
                'SECONDARY INSURANCE': row.get('payer_name_s', ''),
                'SECONDARY ID': row.get('member_id_s', ''),
                'SECONDARY GROUP': '',  # Leave blank as requested
                'TERITARY INSURANCE': row.get('payer_name_t', ''),
                'TERITARY ID': row.get('member_id_t', ''),
                'TERITARY GROUP': '',  # Leave blank as requested
                'INSURANCE TYPE': insurance_type,
                'CO-PAY': '',  # Not available
                # Comorbidities (set YES if matched, NO if not)
                'CORONARY ARTERY DISEASE': comorbidities.get('CORONARY ARTERY DISEASE', 'NO'),
                'ARRHYTHMIA': comorbidities.get('ARRHYTHMIA', 'NO'),
                'CONGESTIVE HEART FAILURE': comorbidities.get('CONGESTIVE HEART FAILURE', 'NO'),
                'PERIPHERAL VASCULAR': comorbidities.get('PERIPHERAL VASCULAR', 'NO'),
                'VALVULAR HEART': comorbidities.get('VALVULAR HEART', 'NO'),
                'CEREBROVASCULAR ACCIDENT': comorbidities.get('CEREBROVASCULAR ACCIDENT', 'NO'),
                'HYPERLIPIDEMIA': comorbidities.get('HYPERLIPIDEMIA', 'NO'),
                'ANGINA PECTORIS': comorbidities.get('ANGINA PECTORIS', 'NO'),
                'HYPOTENSION': comorbidities.get('HYPOTENSION', 'NO'),
                'HYPERTENSION': comorbidities.get('HYPERTENSION', 'NO'),
                'OBESITY': comorbidities.get('OBESITY', 'NO'),
                'DIABETES': comorbidities.get('DIABETES', 'NO'),
                'CHRONIC KIDNEY DISEASE': comorbidities.get('CHRONIC KIDNEY DISEASE', 'NO'),
                'COPD': comorbidities.get('COPD', 'NO'),
                'RESPIRATORY FAILURE': comorbidities.get('RESPIRATORY FAILURE', 'NO'),
                'ASTHMA': comorbidities.get('ASTHMA', 'NO'),
                'SLEEP APNEA': comorbidities.get('SLEEP APNEA', 'NO'),
                'DYSPNEA': comorbidities.get('DYSPNEA', 'NO'),
                'EMPHYSEMA': comorbidities.get('EMPHYSEMA', 'NO'),
                'BRONCHIECTASIS': comorbidities.get('BRONCHIECTASIS', 'NO'),
                'HYPOXEMIA': comorbidities.get('HYPOXEMIA', 'NO'),
                # Diagnosis fields
                'PRIMARY DX': primary_dx,
                'SECONDARY DX': secondary_dx,
                'PRIMARY ICD': primary_icd,
                'SECONDARY ICD': secondary_icd,
                'LAST SEEN DATE': last_seen_date,
                'NEXT APPT': next_appt_date,
                'PROVIDER DATA': row.get('provider_data', ''),
                'PROVIDER NAME': provider_name,
                'CLINIC FACILITY': 'Midwest Cardiology',  # Default clinic
                'PRIMARY CARE PROVIDER': provider_name,  # Same as provider name
                'MEDICATIONS': '',  # Not available
                'ENCOUNTER NOTES': ''  # Not available
            }

            formatted_records.append(record)

        # Create DataFrame and save as Excel with proper date formatting
        output_df = pd.DataFrame(formatted_records, columns=self.template_columns)
        
        # Save to Excel with proper date formatting
        with pd.ExcelWriter(self.output_excel, engine='openpyxl') as writer:
            output_df.to_excel(writer, index=False, sheet_name='Sheet1')
            
            # Get the workbook and worksheet
            workbook = writer.book
            worksheet = writer.sheets['Sheet1']
            
            # Find column indices for date columns
            dob_col_idx = self.template_columns.index('DATE OF BIRTH') + 1  # +1 because Excel is 1-indexed
            last_seen_col_idx = self.template_columns.index('LAST SEEN DATE') + 1
            
            # Apply date formatting to the date columns (skip header row)
            for row_idx in range(2, len(output_df) + 2):  # Start from row 2 (after header)
                # Format DATE OF BIRTH column
                cell = worksheet.cell(row=row_idx, column=dob_col_idx)
                if cell.value is not None and str(cell.value) != 'NaT' and str(cell.value) != 'nan':
                    cell.number_format = 'mm-dd-yyyy'
                
                # Format LAST SEEN DATE column
                cell = worksheet.cell(row=row_idx, column=last_seen_col_idx)
                if cell.value is not None and str(cell.value) != 'NaT' and str(cell.value) != 'nan':
                    cell.number_format = 'mm-dd-yyyy'

        return len(formatted_records)


def main():
    """Main execution function."""
    base_dir = Path("src/MCA")
    cleaned_dir = base_dir / "cleaned"
    output_dir = base_dir / "output"

    # Find the latest consolidated CSV
    csv_files = list(cleaned_dir.glob("consolidated_raw_hbox_*.csv"))
    if not csv_files:
        print("ERROR: No consolidated CSV files found")
        return

    latest_csv = max(csv_files, key=lambda x: x.stat().st_mtime)
    output_excel = output_dir / f"MCA_consolidated_{latest_csv.stem.split('_')[-1]}.xlsx"

    print(f"Input CSV: {latest_csv}")
    print(f"Output Excel: {output_excel}")
    print()

    formatter = TemplateFormatter(str(latest_csv), str(output_excel))
    record_count = formatter.format_data()

    print("✅ Formatted {} records to match template structure".format(record_count))
    print("📊 Output saved to: {}".format(output_excel))


if __name__ == "__main__":
    main()