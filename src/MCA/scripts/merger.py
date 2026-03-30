"""
Medical Database Data Merger Module

This module contains classes for merging different types of medical data.
All operations use raw file I/O without external libraries like pandas.
"""

import os
import csv
from typing import List, Dict, Optional


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
    """Class for merging patients demographics with insurance data."""

    def __init__(self, patients_path: str, insurance_path: str, patient_list_path: str, output_path: str, appointments_path: str = None):
        self.patients_path = patients_path
        self.insurance_path = insurance_path
        self.patient_list_path = patient_list_path
        self.output_path = output_path
        self.appointments_path = appointments_path

    def merge_data(self) -> int:
        """Merge patients, insurance, and patient list data, return number of records."""
        # Read input files
        patients_records = CSVReader.read_csv(self.patients_path)
        insurance_records = CSVReader.read_csv(self.insurance_path)
        patient_list_records = CSVReader.read_csv(self.patient_list_path)

        print(f"Patients file: {len(patients_records)} records")
        print(f"Insurance file: {len(insurance_records)} records")
        print(f"Patient list file: {len(patient_list_records)} records")

        # Create lookup dictionary for insurance data
        insurance_dict = {}
        for record in insurance_records:
            patient_id = record.get('patient_id', '').strip()
            if patient_id:
                # Determine main payer (same logic as before)
                main_payer = record.get('payer_name_s', '').strip()
                main_member_id = record.get('member_id_s', '').strip()

                if not main_payer:
                    main_payer = record.get('payer_name_p', '').strip()
                    main_member_id = record.get('member_id_p', '').strip()

                if not main_payer:
                    main_payer = record.get('payer_name_t', '').strip()
                    main_member_id = record.get('member_id_t', '').strip()

                insurance_dict[patient_id] = {
                    'patient_name': record.get('patient_name', ''),
                    'address': record.get('address', ''),
                    'home_number': record.get('home_number', ''),
                    'mobile_number': record.get('mobile_number', ''),
                    'sex': record.get('sex', ''),
                    'dob': record.get('dob', ''),
                    'member_id': main_member_id,
                    'payer': main_payer,
                    'last_visit': record.get('last_visit', ''),
                    'visit_count': record.get('visit_count', ''),
                    'payer_name_p': record.get('payer_name_p', ''),
                    'member_id_p': record.get('member_id_p', ''),
                    'payer_name_s': record.get('payer_name_s', ''),
                    'member_id_s': record.get('member_id_s', ''),
                    'payer_name_t': record.get('payer_name_t', ''),
                    'member_id_t': record.get('member_id_t', '')
                }

        # Create lookup dictionary for patient list data (keyed by patient_id only)
        patient_list_dict = {}
        for record in patient_list_records:
            patient_id = record.get('patient_id', '').strip()

            if patient_id:
                # Use patient_id as the key for matching
                patient_list_dict[patient_id] = {
                    'address': record.get('address', ''),
                    'city': record.get('city', ''),
                    'state': record.get('state', ''),
                    'zip': record.get('zip', ''),
                    'combined_address': record.get('combined_address', ''),  # Keep for fallback
                    'emergency_contact': record.get('emergency_contact', ''),
                    'emergency_contact_number': record.get('emergency_contact_number', '')
                }

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
        from collections import defaultdict
        patient_groups = defaultdict(list)
        
        # Group records by patient_id
        for record in patients_records:
            patient_id = record.get('patient_id', '').strip()
            if patient_id:
                patient_groups[patient_id].append(record)
        
        merged_records = []
        
        # Process each unique patient
        for patient_id, patient_records in patient_groups.items():
            # Get insurance data for this patient if available
            insurance_data = insurance_dict.get(patient_id, {})
            
            # Get patient list data using patient_id only
            patient_list_data = patient_list_dict.get(patient_id, {})
            
            # Use the first record as the base
            base_record = patient_records[0]
            
            # Get next appointment by matching patient name + dob
            next_appointment = ""
            if appointments_dict:
                from data_cleaner import TextCleaner
                text_cleaner = TextCleaner()
                patient_name = insurance_data.get('patient_name', base_record.get('name', ''))
                dob = insurance_data.get('dob', base_record.get('dob', ''))
                name_key = text_cleaner.normalize_name_key(patient_name)
                dob_key = text_cleaner.normalize_date_key(dob)
                lookup_key = f"{name_key}|{dob_key}"
                next_appointment = appointments_dict.get(lookup_key, "")
            
            # Collect all diagnoses and ICD codes for this patient
            all_diagnoses = []
            all_icds = []
            for record in patient_records:
                diagnosis = record.get('diagnosis', '').strip()
                icd = record.get('icd_code', '').strip()
                if diagnosis:
                    all_diagnoses.append(diagnosis)
                if icd:
                    all_icds.append(icd)
            
            merged_records.append({
                "patient_id": patient_id,
                "patient_name": insurance_data.get('patient_name', base_record.get('name', '')),  # Prefer insurance name
                "address": patient_list_data.get('address', insurance_data.get('address', base_record.get('address', ''))),  # Street address from patient list
                "city": patient_list_data.get('city', ''),  # City from patient list
                "state": patient_list_data.get('state', ''),  # State from patient list
                "zip": patient_list_data.get('zip', ''),  # ZIP from patient list
                "home_number": insurance_data.get('home_number', ''),  # From insurance/visits merge
                "mobile_number": insurance_data.get('mobile_number', ''),  # From insurance/visits merge
                "sex": insurance_data.get('sex', ''),  # From insurance only
                "dob": insurance_data.get('dob', base_record.get('dob', '')),  # Prefer insurance DOB
                "email": base_record.get('email', ''),  # From patients only
                "emergency_contact": patient_list_data.get('emergency_contact', ''),  # From patient list
                "emergency_contact_number": patient_list_data.get('emergency_contact_number', ''),  # From patient list
                "all_diagnoses": "|".join(all_diagnoses),  # Store all diagnoses for comorbidity processing
                "all_icds": "|".join(all_icds),  # Store all ICDs for comorbidity processing
                "member_id": insurance_data.get('member_id', ''),  # From insurance only
                "payer": insurance_data.get('payer', ''),  # From insurance only
                "payer_name_p": insurance_data.get('payer_name_p', ''),
                "member_id_p": insurance_data.get('member_id_p', ''),
                "payer_name_s": insurance_data.get('payer_name_s', ''),
                "member_id_s": insurance_data.get('member_id_s', ''),
                "payer_name_t": insurance_data.get('payer_name_t', ''),
                "member_id_t": insurance_data.get('member_id_t', ''),
                "last_visit": insurance_data.get('last_visit', base_record.get('last_visit_date', '')),  # Prefer insurance last_visit
                "next_appointment": next_appointment,
                "provider_data": base_record.get('provider_data', '')
            })

        # Define output columns
        fieldnames = [
            "patient_id", "patient_name", "address", "city", "state", "zip", "home_number", "mobile_number",
            "sex", "dob", "email", "emergency_contact", "emergency_contact_number",
            "all_diagnoses", "all_icds", "member_id", "payer", "payer_name_p", "member_id_p",
            "payer_name_s", "member_id_s", "payer_name_t", "member_id_t", "last_visit", "next_appointment", "provider_data"
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