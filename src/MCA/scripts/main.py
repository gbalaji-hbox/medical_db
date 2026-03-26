#!/usr/bin/env python3
"""
Medical Database Processing Pipeline

Single execution script that processes all medical data files using modular classes.
Combines insurance data, visits data, and patient demographics into a unified dataset.
Automatically cleans up intermediate files, keeping only the final output.

Usage: python main.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Import Spire.XLS for Excel conversion
try:
    from spire.xls import *
except ImportError:
    print("ERROR: Spire.XLS is required but not installed.")
    print("Install it with: pip install Spire.XLS")
    sys.exit(1)

# Add the scripts directory to Python path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from data_cleaner import (
    InsuranceDataCleaner,
    VisitsDataCleaner,
    PatientsDataCleaner,
    PatientListCleaner,
    AppointmentsDataCleaner
)
from merger import (
    InsuranceVisitsMerger,
    PatientsInsuranceMerger
)
from convert_to_consolidate import TemplateFormatter


def convert_xls_to_xlsx(input_path, output_path=None):
    """
    Convert XLS file to XLSX format using Spire.XLS

    Args:
        input_path (str): Path to input XLS file
        output_path (str, optional): Path for output XLSX file. If None, replaces .xls with .xlsx

    Returns:
        str: Path to the converted XLSX file
    """
    if output_path is None:
        output_path = str(Path(input_path).with_suffix('.xlsx'))

    try:
        print(f"Converting {input_path} to {output_path}...")

        # Create workbook instance
        workbook = Workbook()

        # Load the XLS file
        workbook.LoadFromFile(input_path)

        # Save as XLSX
        workbook.SaveToFile(output_path, ExcelVersion.Version2016)

        # Dispose of the workbook
        workbook.Dispose()

        print(f"✓ Conversion completed: {output_path}")
        return output_path

    except Exception as e:
        print(f"ERROR: Failed to convert {input_path}: {e}")
        raise


def ensure_xlsx_format(file_path):
    """
    Ensure a file is in XLSX format, converting if necessary

    Args:
        file_path (str or Path): Path to the file

    Returns:
        str: Path to the XLSX file (original if already XLSX, converted if XLS)
    """
    file_path = Path(file_path)

    if file_path.suffix.lower() == '.xlsx':
        return str(file_path)
    elif file_path.suffix.lower() == '.xls':
        xlsx_path = file_path.with_suffix('.xlsx')
        return convert_xls_to_xlsx(str(file_path), str(xlsx_path))
    else:
        raise ValueError(f"Unsupported file format: {file_path.suffix}. Expected .xls or .xlsx")


def main():
    """Main execution function for the complete data processing pipeline."""

    print("=== Medical Database Processing Pipeline ===\n")

    # Define file paths
    base_dir = Path(__file__).parent.parent  # This gets src/MCA directory
    cleaned_dir = base_dir / "cleaned"

    # Input files - ensure they are in XLSX format
    insurance_excel = ensure_xlsx_format(base_dir / "Patients by Insurance.xlsx")
    visits_excel = ensure_xlsx_format(base_dir / "Patients With Visits By Insurance.xlsx")
    patients_excel = ensure_xlsx_format(base_dir / "Patients by Diagnosis.xlsx")

    # Handle patient-list file (check for .xls first, then .xlsx)
    patient_list_xls = base_dir / "patient-list.xls"
    patient_list_xlsx = base_dir / "patient-list.xlsx"
    if patient_list_xls.exists():
        patient_list_excel = ensure_xlsx_format(patient_list_xls)
    elif patient_list_xlsx.exists():
        patient_list_excel = str(patient_list_xlsx)
    else:
        patient_list_excel = str(patient_list_xlsx)  # Will be caught by file existence check

    # Handle service by provider file (may not exist)
    service_provider_path = base_dir / "Services by Provider Summary.xlsx"
    service_by_provider_excel = ensure_xlsx_format(service_provider_path) if service_provider_path.exists() else None

    # Handle appointments file
    appointments_excel = ensure_xlsx_format(base_dir / "Appointment Report.xlsx")

    # Intermediate output files
    cleaned_patients_csv = cleaned_dir / "1_patients_by_diagnosis.csv"
    cleaned_insurance_csv = cleaned_dir / "2_patients_by_insurance.csv"
    cleaned_visits_csv = cleaned_dir / "3_patients_with_visits_by_insurance.csv"
    cleaned_patient_list_csv = cleaned_dir / "4_patient_list.csv"
    cleaned_appointments_csv = cleaned_dir / "5_appointments.csv"
    merged_insurance_visits_csv = cleaned_dir / "6_combined_insurance_visits.csv"

    # Final output file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output_csv = cleaned_dir / f"consolidated_raw_hbox_{timestamp}.csv"

    # Check if input files exist
    missing_files = []
    required_files = [
        (insurance_excel, "Patients by Insurance.xlsx"),
        (visits_excel, "Patients With Visits By Insurance.xlsx"),
        (patients_excel, "Patients by Diagnosis.xlsx"),
        (patient_list_excel, "patient-list.xls or patient-list.xlsx"),
        (appointments_excel, "Appointment Report.xlsx")
    ]

    for file_path, original_name in required_files:
        if not Path(file_path).exists():
            missing_files.append(original_name)

    if missing_files:
        print("ERROR: Missing required input files:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease ensure all Excel files are present in the src/MCA/ directory.")
        print("Note: patient-list.xls files will be automatically converted to XLSX format.")
        sys.exit(1)

    try:
        # Step 1: Clean patients by diagnosis data (base file)
        print("Step 1: Cleaning patients by diagnosis data...")
        patients_cleaner = PatientsDataCleaner(
            str(patients_excel),
            str(cleaned_patients_csv),
            str(service_by_provider_excel) if service_by_provider_excel else None
        )
        patients_count = patients_cleaner.clean_data()
        print(f"✓ Patients by diagnosis data cleaned: {patients_count} records\n")

        # Step 2: Clean insurance data
        print("Step 2: Cleaning insurance data...")
        insurance_cleaner = InsuranceDataCleaner(
            str(insurance_excel),
            str(cleaned_insurance_csv)
        )
        insurance_count = insurance_cleaner.clean_data()
        print(f"✓ Insurance data cleaned: {insurance_count} records\n")

        # Step 3: Clean visits data and merge with insurance
        print("Step 3: Cleaning visits data and merging with insurance...")
        visits_cleaner = VisitsDataCleaner(
            str(visits_excel),
            str(cleaned_visits_csv)
        )
        visits_count = visits_cleaner.clean_data()
        print(f"✓ Visits data cleaned: {visits_count} records\n")

        # Merge insurance and visits data
        insurance_visits_merger = InsuranceVisitsMerger(
            str(cleaned_insurance_csv),
            str(cleaned_visits_csv),
            str(merged_insurance_visits_csv)
        )
        merged_count = insurance_visits_merger.merge_data()
        print(f"✓ Insurance and visits data merged: {merged_count} records\n")

        # Step 4: Clean patient list data
        print("Step 4: Cleaning patient list data...")
        patient_list_cleaner = PatientListCleaner(
            str(patient_list_excel),
            str(cleaned_patient_list_csv)
        )
        patient_list_count = patient_list_cleaner.clean_data()
        print(f"✓ Patient list data cleaned: {patient_list_count} records\n")

        # Step 5: Clean appointments data
        print("Step 5: Cleaning appointments data...")
        appointments_cleaner = AppointmentsDataCleaner(
            str(appointments_excel),
            str(cleaned_appointments_csv)
        )
        appointments_count = appointments_cleaner.clean_data()
        print(f"✓ Appointments data cleaned: {appointments_count} records\n")

        # Step 6: Combine all data (patients + insurance/visits + patient list + appointments)
        print("Step 6: Combining all data...")
        final_merger = PatientsInsuranceMerger(
            str(cleaned_patients_csv),
            str(merged_insurance_visits_csv),
            str(cleaned_patient_list_csv),
            str(final_output_csv),
            str(cleaned_appointments_csv)
        )
        final_count = final_merger.merge_data()
        print(f"✓ All data combined: {final_count} records\n")

        # Step 6: Convert to template format
        print("Step 6: Converting to template format...")
        output_dir = base_dir / "output"
        output_excel = output_dir / f"MCA_consolidated_{timestamp}.xlsx"

        formatter = TemplateFormatter(str(final_output_csv), str(output_excel))
        template_count = formatter.format_data()
        print(f"✓ Data converted to template format: {template_count} records")
        print(f"✓ Template Excel saved to: {output_excel}\n")

        # Clean up intermediate files
        print("Step 7: Cleaning up intermediate files...")
        intermediate_files = [
            cleaned_insurance_csv,
            cleaned_visits_csv,
            cleaned_patients_csv,
            cleaned_patient_list_csv,
            cleaned_appointments_csv,
            merged_insurance_visits_csv
            # Note: Keeping final_output_csv for reference
        ]

        cleaned_count = 0
        for file_path in intermediate_files:
            try:
                if file_path.exists():
                    file_path.unlink()
                    cleaned_count += 1
                    print(f"✓ Removed intermediate file: {file_path.name}")
            except Exception as e:
                print(f"⚠️  Warning: Could not remove {file_path.name}: {e}")

        print(f"✓ Cleaned up {cleaned_count} intermediate files\n")

        # Summary
        print("=== Processing Complete ===")
        print(f"📊 Final template: {output_excel}")
        print(f"📄 Raw consolidated CSV: {final_output_csv} (kept for reference)")
        print(f"📈 Total patients: {template_count}")
        print("📋 Template columns: EMR ID, patient names, demographics, insurance, comorbidities,")
        print("                     diagnosis codes, provider data, and all required fields")
        print(f"🧹 Intermediate files cleaned up: {cleaned_count} files removed")
        print("\n✅ All data processing steps completed successfully!")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("Processing failed. Please check the error message above.")
        sys.exit(1)


if __name__ == "__main__":
    main()