# 🏥 Medical Database Processing Pipeline

A unified Python script that processes medical database Excel files and creates a comprehensive patient dataset.

## 📋 Overview

This script combines multiple data sources into a single, clean dataset:
- **📊 Patients by Insurance.xlsx** - Insurance and demographic data
- **📅 Patients With Visits By Insurance.xlsx** - Visit history and insurance data
- **🔍 Patients by Diagnosis.xlsx** - Patient demographics and medical diagnoses
- **📋 patient-list.xlsx** - Additional patient information including addresses and emergency contacts

## ✨ Features

- **🔧 Modular Design**: Separate classes for different data processing tasks
- **⚡ Raw File Operations**: No external libraries required (except openpyxl for Excel reading)
- **🧹 Comprehensive Data Cleaning**: Handles Excel artifacts, phone number formatting, text normalization
- **🤝 Intelligent Merging**: Combines data sources with conflict resolution
- **🛡️ Error Handling**: Graceful error handling with informative messages
- **🔄 Auto XLS Conversion**: Automatically converts .xls files to .xlsx format at runtime

## 📁 File Structure

```
src/MCA/
├── 📊 Patients by Insurance.xlsx
├── 📅 Patients With Visits By Insurance.xlsx
├── 🔍 Patients by Diagnosis.xlsx
├── 📋 patient-list.xlsx
├── 📁 scripts/
│   ├── 🚀 main.py              # Main execution script
│   ├── 🧹 data_cleaner.py      # Classes for cleaning different data types
│   └── 🤝 merger.py           # Classes for merging datasets
├── 📁 cleaned/                 # Intermediate cleaned CSV files
└── 📁 output/                  # Final Excel output files
```

## 🚀 Usage

### 📋 Prerequisites

- 🐍 Python 3.6+
- 📦 Required packages: `openpyxl`, `Spire.XLS` (for Excel conversion)

### ⚙️ Installation

1. **Activate your virtual environment:**
   ```bash
   # On Windows
   .\venv\Scripts\activate
   # On Linux/Mac
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### ▶️ Running the Pipeline

Execute the main script from the project root:

```bash
python src/MCA/scripts/main.py
```

The script will:
1. 🔍 Check for required input files (auto-converts .xls to .xlsx if needed)
2. 🧹 Clean insurance data (~16,205 records)
3. 🧹 Clean visits data (~3,627 records)
4. 🧹 Clean patients data (~13,706 records)
5. 🧹 Clean patient list data and extract emergency contacts
6. 🤝 Merge insurance and visits data
7. 🎯 Create final merged dataset (~21,972 patients)

## 📊 Data Sources & API Integration

### 🔗 API Endpoints
- `eligiblity_patient_insurance` - Patient insurance eligibility data
- `api_patient_profile` - Patient demographic and profile information
- `emr_patient_insurance` - EMR insurance data integration

### 🏥 Supported Cause Codes & ICD Mapping

The system supports the following ICD-10 codes for patient conditions:

| ICD Code | Condition | Suggested Vitals |
|----------|-----------|------------------|
| I35 | Nonrheumatic aortic valve stenosis | BP |
| R09 | Hypoxemia/Chronic hypoxia | O2 |
| R06 | Dyspnea | O2 |
| N18 | Chronic Kidney Disease | BP |
| J96 | Respiratory Failure | O2 |
| J90 | Pleural Effusion | O2 |
| J84 | Pulmonary Fibrosis/Interstitial Lung Disease | O2 |
| J47 | Bronchiectasis | O2 |
| J45 | Asthma | O2 |
| J44 | COPD | O2 |
| J43 | Emphysema | O2 |
| J42 | Chronic Bronchitis | O2 |
| I95 | Hypotension | BP |
| E78 | Hyperlipidemia/Mixed hyperlipidemia | BP |
| I73 | Peripheral Vascular Disease | BP |
| I63 | Cerebrovascular Accident | BP |
| I50 | CHF (Congestive Heart Failure) | BP,WT |
| I49 | Arrhythmia | BP |
| I20 | Angina Pectoris | BP |
| I25 | Coronary Artery Disease | BP |
| G47 | Sleep Apnea | WT |
| E66 | Obesity | WT |
| E11 | Type 2 Diabetes | BG |
| I10 | Hypertension or Pre Hypertensive | BP |

### 🩺 Cause Analysis Example

**Patient Condition Description:**
"Allergies and Adverse Reactions: Environmental allergies; Cardiac and Vasculature: Mixed hyperlipidemia; Nonrheumatic aortic valve stenosis; Genitourinary and Reproductive: Other male erectile dysfunction; BPH without obstruction/lower urinary tract symptoms; Symptoms and Signs: Post-COVID chronic fatigue; Dizziness; Tobacco: Never smoked tobacco"

**Primary Cause:** `I35` (Nonrheumatic aortic valve stenosis) - Critical cardiac condition requiring immediate attention
**Secondary Cause:** `E78` (Mixed hyperlipidemia) - Contributes to cardiovascular risk factors

## 📋 EMR Data Extraction SOP

### 🖥️ EMR Software Access
- **Software:** CGM APRIMA
- **RDP Server:** 65.52.246.229
- **Login User:** 1067475-044
- **Domain:** tiltconnect

### 📊 Report Extraction Steps

#### 1️⃣ Report 1: Patient Demographics and Diagnosis
```
Navigation: Reports > Clinical > Patient by Diagnosis
Filters: Visit span custom date (1-1-2025 to current date)
Export: Excel format → "Patients by Diagnosis.xlsx"
Note: Patients repeat based on primary/secondary diagnoses
```

#### 2️⃣ Report 2: Patient Insurance Details
```
Navigation: Reports > General Reports > Patients by Insurance
Filters: Account option = All Accounts, Effective Date Range (1-1-2025 to current)
Export: Excel format → "Patients by Insurance.xlsx"
Note: No secondary/tertiary insurance details available
```

#### 3️⃣ Report 3: Patients With Visits By Insurance
```
Navigation: Reports > Clinical Quality > Patients With Visits By Insurance
Filters: Visit Dates custom (1-1-2025 to current)
Export: Excel format → "Patients With Visits By Insurance.xlsx"
Note: Ignore patients without insurance
```

#### 4️⃣ Report 4: Services By Provider Summary
```
Navigation: Reports > Clinical > Services By Provider Summary
Filters: Timespan Custom Dates (1-1-2025 to current)
Export: Excel format → "Services by Provider Summary.xlsx"
```

#### 5️⃣ Report 5: Patient Center (Patient List)
```
Navigation: Manage Patients > Patient Center
Settings: Maximum items returned = -1 (no limit)
Export: File > Export to Excel → "patient-list.xls"
Note: Script automatically converts to .xlsx format
```

## 🚀 Quick Start Workflow

1. **📥 Extract Reports** from CGM APRIMA following SOP above
2. **📁 Place Files** in `src/MCA/` directory
3. **🐍 Activate Environment:**
   ```bash
   .\venv\Scripts\activate  # Windows
   source venv/bin/activate # Linux/Mac
   ```
4. **▶️ Run Pipeline:**
   ```bash
   python src/MCA/scripts/main.py
   ```
5. **📊 Find Results:**
   - **Cleaned Data:** `src/MCA/cleaned/consolidated_raw_hbox_[timestamp].csv`
   - **Final Excel:** `src/MCA/output/MCA_consolidated_[timestamp].xlsx`

## 🔧 Data Processing Details

### 🧹 Text Cleaning
- 🗑️ Removes Excel artifacts (`_x000D_`, `_x000A_`)
- 📞 Normalizes phone numbers to `(XXX) XXX-XXXX` format
- ✨ Strips whitespace and line breaks

### 🤝 Data Merging Logic
- 👤 **Patient Names**: Prefers insurance data over patients data
- 🏠 **Addresses**: Prefers patient list combined address over insurance data
- 📞 **Phone Numbers**: Uses insurance data as primary, fills gaps from visits
- 🎂 **DOB**: Prefers insurance data over patients data
- 🚨 **Emergency Contact**: From patient list "Notes Er contact" field
- 📅 **Visit Data**: Uses insurance last_visit, falls back to patients data
- 💳 **Insurance Info**: Primary from insurance data, secondary from visits

### 👥 Patient List Integration
- 🔗 **Matching**: Patients matched by patient_id, name, and DOB combination
- 🏠 **Address Combination**: Address fields combined as: address_2, address_1, city_state
- 🚨 **Emergency Contact**: Preserved from "Notes Er contact" field

### 📞 Phone Number Handling
- 📱 Splits combined phone fields into home/mobile based on type indicators
- 📋 Standardizes formatting across all records
- 💾 Preserves both home and mobile numbers where available

## 🛡️ Error Handling

The script includes comprehensive error handling:
- 📁 File existence checks
- 🔒 Permission error handling
- ✅ Data validation
- 💬 Informative error messages

## 📦 Requirements

- 🐍 Python 3.6+
- 📊 openpyxl>=3.1.5 (for .xlsx file reading)
- 📊 xlrd>=2.0.1 (for .xls file reading)
- 🔄 Spire.XLS>=16.2.0 (for .xls to .xlsx conversion)
- 📁 pathlib (built-in)
- 📊 csv (built-in)
- 🔍 re (built-in)

### 🔗 API Data Structure

The system integrates with EMR APIs supporting the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Unique cause identifier |
| `cause` | String | Condition name/description |
| `icd_code` | String | ICD-10 diagnosis code |
| `active` | Boolean | Whether condition is active |
| `notes` | String | Additional notes/comments |
| `universal` | Boolean | Universal condition flag |
| `created` | DateTime | Record creation timestamp |
| `updated` | DateTime | Last update timestamp |
| `health_care_center_id` | String | Healthcare center identifier |
| `suggested_vitals` | String | Recommended vital sign monitoring (BP, O2, WT, BG)

## 🔧 Troubleshooting

### 🔒 Permission Errors
If you encounter "Permission denied" errors:
1. ❌ Close any programs that might have the CSV files open (Excel, etc.)
2. 🔓 Ensure write permissions in the `src/MCA/cleaned/` directory
3. 🔄 Try running the script again

### 📁 Missing Files
Ensure all required Excel files are present:
- 📊 `src/MCA/Patients by Insurance.xlsx` (or .xls)
- 📅 `src/MCA/Patients With Visits By Insurance.xlsx` (or .xls)
- 🔍 `src/MCA/Patients by Diagnosis.xlsx` (or .xls)
- 📋 `src/MCA/patient-list.xlsx` (or .xls)

> 💡 **Note**: The script automatically converts .xls files to .xlsx format at runtime!

### ⚠️ Import Errors
Make sure you're running from the project root directory so the relative imports work correctly.

## 🏗️ Architecture

The pipeline uses a modular architecture:

### 🧹 Data Cleaning Classes (`data_cleaner.py`)
- 💳 `InsuranceDataCleaner` - Processes insurance Excel files
- 📅 `VisitsDataCleaner` - Processes visits Excel files
- 👥 `PatientsDataCleaner` - Processes patients Excel files
- 📋 `PatientListCleaner` - Processes patient list Excel files

### 🤝 Merger Classes (`merger.py`)
- 💳 `InsuranceVisitsMerger` - Combines insurance and visits data
- 👥 `PatientsInsuranceMerger` - Final merge with patient demographics

### 🚀 Main Script (`main.py`)
- 🎯 Orchestrates the entire pipeline
- 📁 Handles file path management
- 💬 Provides user feedback and error handling
- 🔄 Auto-converts .xls files to .xlsx format

This modular design allows for easy maintenance, testing, and extension of individual components.

## 📸 Screenshots & Documentation

### 📊 EMR Report Extraction
![CGM APRIMA Login](screenshots/cgm_aprima_login.png)
*Screenshot showing CGM APRIMA RDP login screen*

![Patient by Diagnosis Report](screenshots/patient_by_diagnosis_report.png)
*Screenshot of Reports > Clinical > Patient by Diagnosis with date filters applied*

![Patients by Insurance Report](screenshots/patients_by_insurance_report.png)
*Screenshot of Reports > General Reports > Patients by Insurance with filters*

![Patient Center Export](screenshots/patient_center_export.png)
*Screenshot of Patient Center with Maximum items returned = -1 and Export to Excel*

### 🚀 Pipeline Execution
![Pipeline Execution Screenshot](screenshots/pipeline_execution.png)
*Screenshot showing the terminal output when running `python src/MCA/scripts/main.py`*

### 📋 Sample Output Data
![Sample Output Screenshot](screenshots/sample_output.png)
*Screenshot of the final consolidated dataset opened in Excel*

### 📁 File Structure
![File Structure Screenshot](screenshots/file_structure.png)
*Screenshot showing the organized file structure in src/MCA/ after processing*

> 📝 **Note**: Please attach the following screenshots to complete the documentation:
> - `screenshots/cgm_aprima_login.png`: RDP connection and CGM APRIMA login screen
> - `screenshots/patient_by_diagnosis_report.png`: Report generation interface with filters
> - `screenshots/patients_by_insurance_report.png`: Insurance report with account filters
> - `screenshots/patient_center_export.png`: Patient Center export interface
> - `screenshots/pipeline_execution.png`: Terminal output during script execution
> - `screenshots/sample_output.png`: Final Excel output with sample data
> - `screenshots/file_structure.png`: Windows Explorer view of processed files

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