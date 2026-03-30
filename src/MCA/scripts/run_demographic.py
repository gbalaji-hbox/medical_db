#!/usr/bin/env python3
"""
Run demographic schedule processing only
"""

import os
import sys
from pathlib import Path

# Import Spire.XLS for Excel conversion
try:
    from spire.xls import *
except ImportError:
    print("ERROR: Spire.XLS is required but not installed.")
    print("Install it with: pip install Spire.XLS")
    sys.exit(1)

# Add the scripts directory to Python path
script_dir = Path(__file__).parent
sys.path.insert(0, str(script_dir))

from data_cleaner import DemographicScheduleCleaner


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
    """Process demographic schedule data only."""

    # Define file paths
    base_dir = Path(__file__).parent.parent  # This gets src/MCA directory
    cleaned_dir = base_dir / "cleaned"

    # Handle demographic schedule file (check for .xls first, then .xlsx)
    demographic_xls = base_dir / "Demographic by Schedule.xls"
    demographic_xlsx = base_dir / "Demographic by Schedule.xlsx"
    if demographic_xls.exists():
        input_file = ensure_xlsx_format(demographic_xls)
    elif demographic_xlsx.exists():
        input_file = str(demographic_xlsx)
    else:
        print("ERROR: Demographic by Schedule file not found.")
        print("Expected: Demographic by Schedule.xls or Demographic by Schedule.xlsx")
        sys.exit(1)

    output_file = cleaned_dir / "8_demographic_schedule.csv"

    print("=== Demographic Schedule Processing ===")
    print(f"Input: {input_file}")
    print(f"Output: {output_file}")
    print()

    try:
        # Process demographic data
        print("Processing demographic schedule data...")
        cleaner = DemographicScheduleCleaner(
            str(input_file),
            str(output_file)
        )
        record_count = cleaner.clean_data()
        print(f"✓ Demographic schedule data processed: {record_count} records")
        print(f"✓ Output saved to: {output_file}")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()