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

# Add the scripts directory to Python path for imports
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from data_cleaner import (
    InsuranceDataCleaner,
    VisitsDataCleaner,
    PatientsDataCleaner,
    PatientListCleaner
)
from merger import (
    InsuranceVisitsMerger,
    PatientsInsuranceMerger
)
from convert_to_consolidate import TemplateFormatter


def main():
    """Main execution function for the complete data processing pipeline."""

    print("=== Medical Database Processing Pipeline ===\n")

    # Define file paths
    base_dir = Path(__file__).parent.parent  # This gets src/MCA directory
    cleaned_dir = base_dir / "cleaned"

    # Input files
    insurance_excel = base_dir / "Patients by Insurance.xlsx"
    visits_excel = base_dir / "Patients With Visits By Insurance.xlsx"
    patients_excel = base_dir / "Patients by Diagnosis.xlsx"
    patient_list_excel = base_dir / "patient-list.xlsx"
    service_by_provider_excel = base_dir / "Services by Provider Summary.xlsx"

    # Intermediate output files
    cleaned_patients_csv = cleaned_dir / "1_patients_by_diagnosis.csv"
    cleaned_insurance_csv = cleaned_dir / "2_patients_by_insurance.csv"
    cleaned_visits_csv = cleaned_dir / "3_patients_with_visits_by_insurance.csv"
    cleaned_patient_list_csv = cleaned_dir / "4_patient_list.csv"
    merged_insurance_visits_csv = cleaned_dir / "5_combined_insurance_visits.csv"

    # Final output file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_output_csv = cleaned_dir / f"consolidated_raw_hbox_{timestamp}.csv"

    # Check if input files exist
    missing_files = []
    for file_path in [insurance_excel, visits_excel, patients_excel, patient_list_excel]:
        if not file_path.exists():
            missing_files.append(str(file_path))

    if missing_files:
        print("ERROR: Missing required input files:")
        for file in missing_files:
            print(f"  - {file}")
        print("\nPlease ensure all Excel files are present in the src/MCA/ directory.")
        sys.exit(1)

    try:
        # Step 1: Clean patients by diagnosis data (base file)
        print("Step 1: Cleaning patients by diagnosis data...")
        patients_cleaner = PatientsDataCleaner(
            str(patients_excel),
            str(cleaned_patients_csv),
            str(service_by_provider_excel) if service_by_provider_excel.exists() else None
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

        # Step 5: Combine all data (patients + insurance/visits + patient list)
        print("Step 5: Combining all data...")
        final_merger = PatientsInsuranceMerger(
            str(cleaned_patients_csv),
            str(merged_insurance_visits_csv),
            str(cleaned_patient_list_csv),
            str(final_output_csv)
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