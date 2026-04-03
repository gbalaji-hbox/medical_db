"""
Medical Database Data Merger Module

This module contains classes for merging different types of medical data.
All operations use raw file I/O without external libraries like pandas.
"""

import os
import csv
from typing import List, Dict, Optional
from pathlib import Path
from collections import defaultdict


class CSVReader:
    """Basic CSV file reader using raw file operations."""

    @staticmethod
    def read_csv(file_path: str) -> List[Dict]:
        """Read CSV file and return list of dictionaries."""
        records = []
        with open(file_path, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                records.append(row)
        return records


class CSVWriter:
    """Basic CSV file writer using raw file operations."""

    @staticmethod
    def write_csv(file_path: str, records: List[Dict], fieldnames: List[str]) -> None:
        """Write records to CSV file."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)


class InsuranceVisitsMerger:
    """Class for merging insurance and visits data."""

    def __init__(self, insurance_path: str, visits_path: str, output_path: str):
        self.insurance_path = insurance_path
        self.visits_path = visits_path
        self.output_path = output_path

    def merge_data(self) -> int:
        """Merge insurance and visits data, return number of records."""
        # Read input files
        insurance_records = CSVReader.read_csv(self.insurance_path)
        visits_records = CSVReader.read_csv(self.visits_path)

        print(f"Insurance file: {len(insurance_records)} records")
        print(f"Visits file: {len(visits_records)} records")

        # Create lookup dictionary for visits data
        visits_dict = {}
        for record in visits_records:
            patient_id = record.get('patient_id', '').strip()
            if patient_id:
                phone_num = record.get('phone_number', '').strip()
                phone_type = record.get('phone_type', '').strip().lower()

                # Split phone data into home/mobile columns based on type
                visits_home = phone_num if phone_type == 'home' else ''
                visits_mobile = phone_num if phone_type == 'cell' else ''

                # Determine main payer for visits (same logic as insurance)
                visits_main_payer = record.get('payer_name_s', '').strip()
                visits_main_member_id = record.get('member_id_s', '').strip()

                if not visits_main_payer:
                    visits_main_payer = record.get('payer_name_p', '').strip()
                    visits_main_member_id = record.get('member_id_p', '').strip()

                if not visits_main_payer:
                    visits_main_payer = record.get('payer_name_t', '').strip()
                    visits_main_member_id = record.get('member_id_t', '').strip()

                visits_dict[patient_id] = {
                    'home_number': visits_home,
                    'mobile_number': visits_mobile,
                    'last_visit': record.get('last_visit', ''),
                    'visit_count': record.get('visit_count', ''),
                    'visits_member_id': visits_main_member_id,
                    'visits_payer': visits_main_payer
                }

        # Process insurance data and add visit information
        merged_records = []

        for record in insurance_records:
            patient_id = record.get('patient_id', '').strip()

            # Get visit data for this patient if available
            visit_data = visits_dict.get(patient_id, {})

            # Use secondary insurance as the main payer (since that's what's populated)
            main_payer = record.get('payer_name_s', '').strip()
            main_member_id = record.get('member_id_s', '').strip()

            # If no secondary, try primary
            if not main_payer:
                main_payer = record.get('payer_name_p', '').strip()
                main_member_id = record.get('member_id_p', '').strip()

            # If no primary, try tertiary
            if not main_payer:
                main_payer = record.get('payer_name_t', '').strip()
                main_member_id = record.get('member_id_t', '').strip()

            # Use insurance member_id, but fall back to visits member_id if insurance doesn't have it
            final_member_id = main_member_id if main_member_id else visit_data.get('visits_member_id', '')

            # Use insurance phone numbers as primary, fill in from visits if missing
            final_home = record.get('home_number', '').strip()
            final_mobile = record.get('mobile_number', '').strip()

            # If insurance doesn't have home number, use from visits
            if not final_home:
                final_home = visit_data.get('home_number', '')

            # If insurance doesn't have mobile number, use from visits
            if not final_mobile:
                final_mobile = visit_data.get('mobile_number', '')

            merged_records.append({
                "patient_id": patient_id,
                "patient_name": record.get('patient_name', ''),
                "address": record.get('address', ''),
                "home_number": final_home,
                "mobile_number": final_mobile,
                "sex": record.get('sex', ''),
                "dob": record.get('dob', ''),
                "member_id": final_member_id,
                "payer": main_payer,
                "payer_name_p": record.get('payer_name_p', ''),
                "member_id_p": record.get('member_id_p', ''),
                "payer_name_s": record.get('payer_name_s', ''),
                "member_id_s": record.get('member_id_s', ''),
                "payer_name_t": record.get('payer_name_t', ''),
                "member_id_t": record.get('member_id_t', ''),
                "last_visit": visit_data.get('last_visit', ''),
                "visit_count": visit_data.get('visit_count', '')
            })

        # Add any patients that are ONLY in visits file (no insurance data)
        for patient_id, visit_data in visits_dict.items():
            # Check if this patient is already in merged_records
            existing_ids = {record['patient_id'] for record in merged_records}
            if patient_id not in existing_ids:
                merged_records.append({
                    "patient_id": patient_id,
                    "patient_name": '',  # Not available
                    "address": '',  # Not available
                    "home_number": visit_data.get('home_number', ''),
                    "mobile_number": visit_data.get('mobile_number', ''),
                    "sex": '',  # Not available
                    "dob": '',  # Not available
                    "member_id": visit_data.get('visits_member_id', ''),
                    "payer": visit_data.get('visits_payer', ''),
                    "payer_name_p": '',  # Not available for visits-only
                    "member_id_p": '',
                    "payer_name_s": '',  # Not available for visits-only
                    "member_id_s": '',
                    "payer_name_t": '',  # Not available for visits-only
                    "member_id_t": '',
                    "last_visit": visit_data.get('last_visit', ''),
                    "visit_count": visit_data.get('visit_count', '')
                })

        # Define output columns
        fieldnames = [
            "patient_id", "patient_name", "address", "home_number", "mobile_number",
            "sex", "dob", "member_id", "payer", "payer_name_p", "member_id_p",
            "payer_name_s", "member_id_s", "payer_name_t", "member_id_t", "last_visit", "visit_count"
        ]

        # Write merged data
        CSVWriter.write_csv(self.output_path, merged_records, fieldnames)
        return len(merged_records)


class PatientsInsuranceMerger:
    """Class for merging base data with secondary data."""

    def __init__(self, base_path: str, secondary_path: str, patient_list_path: str, output_path: str, appointments_path: str = None):
        self.base_path = base_path
        self.secondary_path = secondary_path
        self.patient_list_path = patient_list_path
        self.output_path = output_path
        self.appointments_path = appointments_path
        self.cause_mapping = self._load_cause_mapping()

    def _load_cause_mapping(self) -> Dict[str, str]:
        """Load cause to ICD mapping from api_prescriptioncauselist.csv."""
        cause_file = Path(__file__).parent.parent / 'template' / 'api_prescriptioncauselist_202603101243.csv'
        icd_to_cause = {}
        with open(cause_file, 'r', encoding='utf-8-sig') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                icd = row.get('icd_code', '').strip()
                cause = row.get('cause', '').strip()
                if icd and cause:
                    icd_to_cause[icd] = cause
        return icd_to_cause

    def _is_icd_supported(self, icd: str) -> bool:
        """Check if ICD code is supported (matches the cause mapping)."""
        if not icd:
            return False
        
        # Try exact match first
        if icd in self.cause_mapping:
            return True
        
        # Try range matching with special diabetes handling
        diabetes_codes = ['E10', 'E11', 'E13']
        if any(icd.startswith(code) for code in diabetes_codes):
            # Check if diabetes is in mapping
            for mapped_icd, cause_name in self.cause_mapping.items():
                if cause_name == 'Type 2 Diabetes':
                    return True
        else:
            # Regular range matching
            for mapped_icd in self.cause_mapping:
                if icd.startswith(mapped_icd.split('.')[0]):
                    return True
        
        return False

    def merge_data(self) -> int:
        """Merge base, secondary, and patient list data, return number of records."""
        # Read input files
        base_records = CSVReader.read_csv(self.base_path)
        secondary_records = CSVReader.read_csv(self.secondary_path)
        patient_list_records = CSVReader.read_csv(self.patient_list_path)

        print(f"Base file: {len(base_records)} records")
        print(f"Secondary file: {len(secondary_records)} records")
        print(f"Patient list file: {len(patient_list_records)} records")

        # Create lookup dictionary for secondary data (keyed by normalized name + dob)
        secondary_dict = {}
        for record in secondary_records:
            patient_name = record.get('name', '').strip()
            dob = record.get('dob', '').strip()
            if patient_name and dob:
                # Create normalized key
                from data_cleaner import TextCleaner
                text_cleaner = TextCleaner()
                name_key = text_cleaner.normalize_name_key(patient_name)
                dob_key = text_cleaner.normalize_date_key(dob)
                lookup_key = f"{name_key}|{dob_key}"
                
                secondary_dict[lookup_key] = {
                    'patient_id': record.get('patient_id', ''),
                    'patient_name': patient_name,
                    'address': record.get('address', ''),
                    'dob': dob,
                    'email': record.get('email', ''),
                    'all_diagnoses': record.get('all_diagnoses', ''),
                    'all_icds': record.get('all_icds', ''),
                    'medication': record.get('medication', ''),
                    'provider_data': record.get('provider_data', ''),
                    'provider_name': record.get('provider_name', ''),
                    'primary_care_provider': record.get('primary_care_provider', '')
                }

        # Create lookup dictionary for patient list data (keyed by name+DOB and patient_id)
        patient_list_dict = {}
        for record in patient_list_records:
            patient_id = record.get('patient_id', '').strip()
            patient_name = record.get('patient_name', '').strip()
            dob = record.get('dob', '').strip()

            # Create data dict
            data = {
                'address': record.get('address', ''),
                'city': record.get('city', ''),
                'state': record.get('state', ''),
                'zip': record.get('zip', ''),
                'combined_address': record.get('combined_address', ''),  # Keep for fallback
                'emergency_contact': record.get('emergency_contact', ''),
                'emergency_contact_number': record.get('emergency_contact_number', '')
            }

            # Key by patient_id
            if patient_id:
                patient_list_dict[patient_id] = data
            
            # Also key by name+DOB for matching
            if patient_name and dob:
                from data_cleaner import TextCleaner
                text_cleaner = TextCleaner()
                name_key = text_cleaner.normalize_name_key(patient_name)
                dob_key = text_cleaner.normalize_date_key(dob)
                lookup_key = f"{name_key}|{dob_key}"
                patient_list_dict[lookup_key] = data

        # Create lookup dictionary for appointments data (keyed by normalized patient name + dob)
        appointments_dict = {}
        if self.appointments_path and os.path.exists(self.appointments_path):
            appointments_records = CSVReader.read_csv(self.appointments_path)
            print(f"Appointments file: {len(appointments_records)} records")
            
            for record in appointments_records:
                patient_name = record.get('patient_name', '').strip()
                dob = record.get('dob', '').strip()
                phone = record.get('phone', '').strip()
                datetime_val = record.get('datetime', '').strip()
                
                if patient_name and dob:
                    # Create a key for matching: normalized name + dob
                    from data_cleaner import TextCleaner
                    text_cleaner = TextCleaner()
                    name_key = text_cleaner.normalize_name_key(patient_name)
                    dob_key = text_cleaner.normalize_date_key(dob)
                    lookup_key = f"{name_key}|{dob_key}"
                    
                    # Store the earliest appointment datetime
                    if lookup_key not in appointments_dict or datetime_val < appointments_dict[lookup_key]:
                        appointments_dict[lookup_key] = datetime_val

        # Merge data with intelligent deduplication - keep all diagnoses per patient
        patient_groups = defaultdict(list)
        
        # Group base records by patient_id
        for record in base_records:
            patient_id = record.get('patient_id', '').strip()
            if patient_id:
                patient_groups[patient_id].append(record)
        
        merged_records = []
        
        # Process each unique patient
        for patient_id, base_records_list in patient_groups.items():
            # Get secondary data by matching name + DOB
            base_record = base_records_list[0]
            patient_name = base_record.get('patient_name', '')
            dob = base_record.get('dob', '')
            
            secondary_data = {}
            if patient_name and dob:
                from data_cleaner import TextCleaner
                text_cleaner = TextCleaner()
                name_key = text_cleaner.normalize_name_key(patient_name)
                dob_key = text_cleaner.normalize_date_key(dob)
                lookup_key = f"{name_key}|{dob_key}"
                secondary_data = secondary_dict.get(lookup_key, {})
            
            # Determine main payer (prefer primary over secondary)
            main_payer = base_record.get('payer_name_p', '').strip()
            if not main_payer:
                main_payer = base_record.get('payer_name_s', '').strip()
            if not main_payer:
                main_payer = base_record.get('payer_name_t', '').strip()
            
            # Determine main member ID (prefer primary over secondary)
            main_member_id = base_record.get('member_id_p', '').strip()
            if not main_member_id:
                main_member_id = base_record.get('member_id_s', '').strip()
            if not main_member_id:
                main_member_id = base_record.get('member_id_t', '').strip()
            
            # Get next appointment by matching patient name + dob
            next_appointment = ""
            if appointments_dict and patient_name and dob:
                next_appointment = appointments_dict.get(lookup_key, "")
            
            # Get patient list data - try to match by name + DOB
            patient_list_data = {}
            if patient_name and dob:
                patient_list_data = patient_list_dict.get(lookup_key, {})
            # Fallback to patient_id matching if name+DOB didn't work
            if not patient_list_data and patient_id:
                patient_list_data = patient_list_dict.get(patient_id, {})
            
            # Get all diagnoses and ICD codes from secondary data
            all_diagnoses = secondary_data.get('all_diagnoses', '')
            all_icds = secondary_data.get('all_icds', '')
            
            # Skip patients without diagnosis data
            has_supported_icd = False
            if all_icds:
                icds_list = [icd.strip() for icd in all_icds.split('|') if icd.strip()]
                has_supported_icd = any(self._is_icd_supported(icd) for icd in icds_list)
            if not has_supported_icd:
                continue

            merged_records.append({
                "patient_id": patient_id,
                "patient_name": base_record.get('patient_name', secondary_data.get('patient_name', '')),  # Prefer base name
                "address": patient_list_data.get('address', base_record.get('address', secondary_data.get('address', ''))),  # Street address from patient list
                "city": patient_list_data.get('city', ''),  # City from patient list
                "state": patient_list_data.get('state', ''),  # State from patient list
                "zip": patient_list_data.get('zip', ''),  # ZIP from patient list
                "home_number": base_record.get('home_number', ''),  # From base/visits merge
                "mobile_number": base_record.get('mobile_number', ''),  # From base/visits merge
                "sex": base_record.get('sex', ''),  # From base only
                "dob": base_record.get('dob', secondary_data.get('dob', '')),  # Prefer base DOB
                "email": secondary_data.get('email', ''),  # From secondary only
                "emergency_contact": patient_list_data.get('emergency_contact', ''),  # From patient list
                "emergency_contact_number": patient_list_data.get('emergency_contact_number', ''),  # From patient list
                "all_diagnoses": all_diagnoses,  # From secondary data
                "all_icds": all_icds,  # From secondary data
                "member_id": main_member_id,  # From base only
                "payer": main_payer,  # From base only
                "payer_name_p": base_record.get('payer_name_p', ''),
                "member_id_p": base_record.get('member_id_p', ''),
                "payer_name_s": base_record.get('payer_name_s', ''),
                "member_id_s": base_record.get('member_id_s', ''),
                "payer_name_t": base_record.get('payer_name_t', ''),
                "member_id_t": base_record.get('member_id_t', ''),
                "last_visit": base_record.get('last_visit', ''),  # From base
                "next_appointment": next_appointment,
                "provider_data": secondary_data.get('provider_data', ''),
                "provider_name": secondary_data.get('provider_name', ''),
                "primary_care_provider": secondary_data.get('primary_care_provider', ''),
                "medication": secondary_data.get('medication', '')
            })

        # Define output columns
        fieldnames = [
            "patient_id", "patient_name", "address", "city", "state", "zip", "home_number", "mobile_number",
            "sex", "dob", "email", "emergency_contact", "emergency_contact_number",
            "all_diagnoses", "all_icds", "member_id", "payer", "payer_name_p", "member_id_p",
            "payer_name_s", "member_id_s", "payer_name_t", "member_id_t", "last_visit", "next_appointment", 
            "provider_data", "provider_name", "primary_care_provider", "medication"
        ]

        # Write final merged data
        CSVWriter.write_csv(self.output_path, merged_records, fieldnames)
        return len(merged_records)


class CopayMerger:
    """Class for merging copay data with patient list data."""

    def __init__(self, patient_list_path: str, copay_path: str, output_path: str):
        self.patient_list_path = patient_list_path
        self.copay_path = copay_path
        self.output_path = output_path

    def merge_data(self) -> int:
        """Merge patient list with copay data, return number of records."""
        # Read input files
        patient_records = CSVReader.read_csv(self.patient_list_path)
        copay_records = CSVReader.read_csv(self.copay_path)

        print(f"Patient list file: {len(patient_records)} records")
        print(f" Copay file: {len(copay_records)} records")

        # Create lookup dictionary for copay data (keyed by normalized patient name + primary insurance)
        from data_cleaner import TextCleaner
        text_cleaner = TextCleaner()
        copay_dict = {}

        for record in copay_records:
            patient_name = record.get('patient_name', '').strip()
            primary_insurance = record.get('primary_insurance', '').strip()
            actual_copay = record.get('actual_copay', 0.0)

            if patient_name and primary_insurance:
                # Create a key for matching: normalized name + normalized insurance
                name_key = text_cleaner.normalize_name_key(patient_name)
                insurance_key = text_cleaner.normalize_name_key(primary_insurance)
                lookup_key = f"{name_key}|{insurance_key}"

                copay_dict[lookup_key] = actual_copay

        # Merge copay data into patient records
        merged_records = []

        for record in patient_records:
            patient_name = record.get('patient_name', '').strip()
            primary_insurance = record.get('payer', '').strip()  # Assuming 'payer' is the primary insurance field

            # Try to find matching copay
            copay_amount = 0.0
            if patient_name and primary_insurance:
                name_key = text_cleaner.normalize_name_key(patient_name)
                insurance_key = text_cleaner.normalize_name_key(primary_insurance)
                lookup_key = f"{name_key}|{insurance_key}"
                copay_amount = copay_dict.get(lookup_key, 0.0)

            # Add copay to the record
            record['copay'] = copay_amount
            merged_records.append(record)

        # Define output columns (add copay to existing fieldnames)
        fieldnames = list(merged_records[0].keys()) if merged_records else []

        # Write merged data
        CSVWriter.write_csv(self.output_path, merged_records, fieldnames)
        return len(merged_records)