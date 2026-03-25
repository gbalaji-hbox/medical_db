# Medical Database Processing Pipeline

A unified Python script that processes medical database Excel files and creates a comprehensive patient dataset.

## Overview

This script combines multiple data sources into a single, clean dataset:
- **Patients by Insurance.xlsx** - Insurance and demographic data
- **Patients With Visits By Insurance.xlsx** - Visit history and insurance data
- **Patients by Diagnosis.xlsx** - Patient demographics and medical diagnoses
- **patient-list.xls** - Additional patient information including addresses and emergency contacts

## Features

- **Modular Design**: Separate classes for different data processing tasks
- **Raw File Operations**: No external libraries required (except openpyxl for Excel reading)
- **Comprehensive Data Cleaning**: Handles Excel artifacts, phone number formatting, text normalization
- **Intelligent Merging**: Combines data sources with conflict resolution
- **Error Handling**: Graceful error handling with informative messages

## File Structure

```
src/MCA/scripts/
├── main.py              # Main execution script
├── data_cleaner.py      # Classes for cleaning different data types
└── merger.py           # Classes for merging datasets
```

## Usage

### Prerequisites

- Python 3.6+
- Required packages: `openpyxl` (for Excel reading)

### Installation

1. Activate your virtual environment:
   ```bash
   # On Windows
   .\venv\Scripts\activate
   # On Linux/Mac
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Pipeline

Execute the main script from the project root:

```bash
python src/MCA/scripts/main.py
```

The script will:
1. Check for required input files
2. Clean insurance data (16,205 records)
3. Clean visits data (3,627 records)
4. Clean patients data (13,706 records)
5. Clean patient list data and extract emergency contacts
6. Merge insurance and visits data
7. Create final merged dataset (21,972 patients)

## Output

### Final Dataset: `final_merged_patients_insurance.csv`

**Location**: `src/MCA/cleaned/final_merged_patients_insurance.csv`

**Columns** (15 total):
- `patient_id` - Unique patient identifier
- `patient_name` - Patient full name
- `address` - Patient address (combined from patient list)
- `home_number` - Home phone number
- `mobile_number` - Mobile phone number
- `sex` - Patient gender (M/F)
- `dob` - Date of birth
- `email` - Patient email address
- `diagnosis` - Medical diagnosis description
- `icd_code` - ICD diagnosis code
- `member_id` - Insurance member ID
- `payer` - Insurance payer name
- `last_visit` - Date of last visit
- `visit_count` - Total number of visits
- `emergency_contact` - Emergency contact information

### Intermediate Files

The script also creates intermediate cleaned files:
- `cleaned_insurance.csv` - Processed insurance data
- `cleaned_visits_insurance.csv` - Processed visits data
- `cleaned_patients.csv` - Processed patients data
- `merged_insurance_visits.csv` - Combined insurance and visits data

## Data Processing Details

### Text Cleaning
- Removes Excel artifacts (`_x000D_`, `_x000A_`)
- Normalizes phone numbers to `(XXX) XXX-XXXX` format
- Strips whitespace and line breaks

### Data Merging Logic
- **Patient Names**: Prefers insurance data over patients data
- **Addresses**: Prefers patient list combined address (address_2 + address_1 + city_state) over insurance data
- **Phone Numbers**: Uses insurance data as primary, fills gaps from visits
- **DOB**: Prefers insurance data over patients data
- **Emergency Contact**: From patient list "Notes Er contact" field
- **Visit Data**: Uses insurance last_visit, falls back to patients data
- **Insurance Info**: Primary from insurance data, secondary from visits

### Patient List Integration
- **Matching**: Patients matched by patient_id, name, and DOB combination
- **Address Combination**: Address fields combined as: address_2, address_1, city_state
- **Emergency Contact**: Preserved from "Notes Er contact" field with format "Name, relationship and Number"

### Phone Number Handling
- Splits combined phone fields into home/mobile based on type indicators
- Standardizes formatting across all records
- Preserves both home and mobile numbers where available

## Error Handling

The script includes comprehensive error handling:
- File existence checks
- Permission error handling
- Data validation
- Informative error messages

## Requirements

- Python 3.6+
- openpyxl>=3.1.5 (for .xlsx file reading)
- xlrd>=2.0.1 (for .xls file reading)
- pathlib (built-in)
- csv (built-in)
- re (built-in)

## Troubleshooting

### Permission Errors
If you encounter "Permission denied" errors:
1. Close any programs that might have the CSV files open (Excel, etc.)
2. Ensure write permissions in the `src/MCA/cleaned/` directory
3. Try running the script again

### Missing Files
Ensure all required Excel files are present:
- `src/MCA/Patients by Insurance.xlsx`
- `src/MCA/Patients With Visits By Insurance.xlsx`
- `src/MCA/Patients by Diagnosis.xlsx`

### Import Errors
Make sure you're running from the project root directory so the relative imports work correctly.

## Architecture

The pipeline uses a modular architecture:

### Data Cleaning Classes (`data_cleaner.py`)
- `InsuranceDataCleaner` - Processes insurance Excel files
- `VisitsDataCleaner` - Processes visits Excel files
- `PatientsDataCleaner` - Processes patients Excel files

### Merger Classes (`merger.py`)
- `InsuranceVisitsMerger` - Combines insurance and visits data
- `PatientsInsuranceMerger` - Final merge with patient demographics

### Main Script (`main.py`)
- Orchestrates the entire pipeline
- Handles file path management
- Provides user feedback and error handling

This modular design allows for easy maintenance, testing, and extension of individual components.</content>
<parameter name="filePath">d:\Work_Folder\medical_db\README.md