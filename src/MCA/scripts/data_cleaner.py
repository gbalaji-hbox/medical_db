"""
Medical Database Data Cleaner Module

This module contains classes for cleaning different types of medical data files.
All operations use raw file I/O without external libraries like pandas.
"""

import os
import re
import csv
from typing import List, Dict, Tuple, Optional


class TextCleaner:
    """Utility class for cleaning text data."""

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean text by replacing Excel artifacts and normalizing whitespace."""
        if not text:
            return ""
        return (text.replace('_x000D_', ',')
                .replace('_x000A_', ',')
                .replace('\n', ',')
                .replace('\r', '')
                .strip())

    @staticmethod
    def normalize_phone(phone: str) -> str:
        """Normalize phone number format to (XXX) XXX-XXXX. Only accepts exactly 10 digits."""
        if not phone:
            return ""

        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return ""  # Reject anything that's not exactly 10 digits

    @staticmethod
    def normalize_name_key(name: str) -> str:
        """Normalize patient name for matching keys."""
        if not name:
            return ""
        normalized = name.strip().lower().replace(",", " ")
        return re.sub(r"\s+", " ", normalized).strip()

    @staticmethod
    def normalize_date_key(date_raw: str) -> str:
        """Normalize dates like MM/DD/YYYY or M/D/YYYY to MM/DD/YYYY for matching."""
        if not date_raw:
            return ""
        cleaned = date_raw.strip()
        if " " in cleaned:
            cleaned = cleaned.split(" ", 1)[0]
        cleaned = cleaned.replace("-", "/")
        parts = [part.strip() for part in cleaned.split("/") if part.strip()]
        if len(parts) == 3 and all(part.isdigit() for part in parts):
            if len(parts[0]) == 4:
                year, month, day = parts
            else:
                month, day, year = parts
            month = month.zfill(2)
            day = day.zfill(2)
            if len(year) == 4:
                return f"{month}/{day}/{year}"
        return cleaned


class ExcelReader:
    """Basic Excel file reader using openpyxl for .xlsx files."""

    @staticmethod
    def read_excel_rows(file_path: str, start_row: int = 0) -> List[List[str]]:
        """Read Excel file rows starting from specified row index."""
        try:
            import openpyxl
            workbook = openpyxl.load_workbook(file_path, data_only=True)
            sheet = workbook.active

            rows = []
            for row_idx, row in enumerate(sheet.iter_rows(min_row=start_row + 1, values_only=True), start_row):
                # Convert all values to strings and handle None values
                row_data = [str(cell) if cell is not None else "" for cell in row]
                rows.append(row_data)

            return rows
        except ImportError:
            raise ImportError("openpyxl is required for Excel file reading. Install with: pip install openpyxl")


class InsuranceDataCleaner:
    """Class for cleaning insurance data from Excel files."""

    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.text_cleaner = TextCleaner()

    def parse_phone(self, phone_raw: str) -> Tuple[str, str]:
        """Extract home and mobile numbers from phone field."""
        if not phone_raw:
            return "", ""

        # Normalize whitespace and Excel artifacts
        phone_raw = (phone_raw.replace("\n", " ")
                    .replace("\r", " ")
                    .replace("_x000D_", " ")
                    .replace("_x000A_", " "))

        # Find all phone number patterns
        numbers = re.findall(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", phone_raw)
        home_num = self.text_cleaner.normalize_phone(numbers[0]) if len(numbers) > 0 else ""
        cell_num = self.text_cleaner.normalize_phone(numbers[1]) if len(numbers) > 1 else ""

        return home_num, cell_num

    def extract_payer_info(self, account_raw: str) -> Tuple[str, str]:
        """Return (payer_type, payer_name) from Account Name like 'Main (S)'."""
        if not account_raw:
            return "", ""

        # Extract type inside parentheses
        type_match = re.search(r"\(([PpSsTt])\)", account_raw)
        payer_type = type_match.group(1).upper() if type_match else ""

        # Extract name before parentheses
        payer_name = account_raw.split("(")[0].strip()
        return payer_type, payer_name

    def clean_data(self) -> int:
        """Clean insurance data and return number of records processed."""
        # Read Excel data starting from row 20 (header at index 19)
        rows = ExcelReader.read_excel_rows(self.input_path, start_row=20)

        patients = {}
        current_payer = ""

        for row in rows:
            if len(row) < 13:  # Skip incomplete rows
                continue

            # Extract fields by column index
            pay = row[0].strip() if len(row) > 0 else ""
            pid = row[2].strip() if len(row) > 2 else ""
            mid = row[4].strip() if len(row) > 4 else ""
            pname = row[5].strip() if len(row) > 5 else ""
            addr = row[6].strip() if len(row) > 6 else ""
            pnum = row[7].strip() if len(row) > 7 else ""
            acc = row[8].strip() if len(row) > 8 else ""
            sex = row[11].strip() if len(row) > 11 else ""
            dob = row[12].strip() if len(row) > 12 else ""

            # Update current payer if this row has a payer header
            if pay:
                current_payer = pay

            # Parse phone numbers
            home_number, mobile_number = self.parse_phone(pnum)

            # Skip rows that don't have patient data
            if not pname or not pid:
                continue

            # Initialize patient record if not exists
            if pid not in patients:
                patients[pid] = {
                    "patient_name": self.text_cleaner.clean_text(pname),
                    "address": self.text_cleaner.clean_text(addr),
                    "home_number": home_number,
                    "mobile_number": mobile_number,
                    "sex": sex,
                    "dob": dob,
                    "payers": []
                }

            # Add payer info
            patients[pid]["payers"].append((current_payer, mid))

        # Now create records, assigning payers in order
        records = []
        for pid, data in patients.items():
            record = {
                "patient_id": pid,
                "patient_name": data["patient_name"],
                "address": data["address"],
                "home_number": data["home_number"],
                "mobile_number": data["mobile_number"],
                "sex": data["sex"],
                "dob": data["dob"],
                "payer_name_p": "",
                "member_id_p": "",
                "payer_name_s": "",
                "member_id_s": "",
                "payer_name_t": "",
                "member_id_t": ""
            }

            # Assign payers
            for i, (payer_name, member_id) in enumerate(data["payers"][:3]):  # Up to 3
                if i == 0:
                    record["payer_name_p"] = payer_name
                    record["member_id_p"] = member_id
                elif i == 1:
                    record["payer_name_s"] = payer_name
                    record["member_id_s"] = member_id
                elif i == 2:
                    record["payer_name_t"] = payer_name
                    record["member_id_t"] = member_id

            records.append(record)

        # Write to CSV
        self._write_csv(records)
        return len(records)

    def _write_csv(self, records: List[Dict]) -> None:
        """Write records to CSV file."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        fieldnames = [
            "patient_id", "patient_name", "address", "home_number", "mobile_number",
            "sex", "dob", "payer_name_p", "member_id_p", "payer_name_s", "member_id_s",
            "payer_name_t", "member_id_t"
        ]

        with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)


class VisitsDataCleaner:
    """Class for cleaning visits data from Excel files."""

    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.text_cleaner = TextCleaner()

    def parse_patient_id_name(self, id_name_raw: str) -> Tuple[str, str]:
        """Extract patient ID and name from format like '109051/Ahamed, Yahah'."""
        if not id_name_raw or "/" not in id_name_raw:
            return "", ""

        parts = id_name_raw.split("/", 1)
        if len(parts) == 2:
            patient_id = parts[0].strip()
            patient_name = parts[1].strip()
            return patient_id, patient_name
        return "", id_name_raw.strip()

    def parse_phone_with_type(self, phone_raw: str) -> Tuple[str, str]:
        """Extract phone number and type from format like '(929)250-4549 cell'."""
        if not phone_raw:
            return "", ""

        # Normalize whitespace
        phone_raw = phone_raw.replace("\n", " ").replace("\r", " ").replace("_x000d_", " ")

        # Extract phone number
        phone_match = re.search(r"(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})", phone_raw)
        phone_number = self.text_cleaner.normalize_phone(phone_match.group(1)) if phone_match else ""

        # Extract type
        phone_type = ""
        if "home" in phone_raw.lower():
            phone_type = "home"
        elif "cell" in phone_raw.lower():
            phone_type = "cell"

        return phone_number, phone_type

    def clean_data(self) -> int:
        """Clean visits data and return number of records processed."""
        # Read Excel data starting from row 14 (header at index 13)
        rows = ExcelReader.read_excel_rows(self.input_path, start_row=14)

        patients = {}
        current_payer = ""

        for row in rows:
            if len(row) < 8:  # Skip incomplete rows
                continue

            # Extract fields by column index
            pay = row[0].strip() if len(row) > 0 else ""
            mid = row[2].strip() if len(row) > 2 else ""
            pid_name = row[3].strip() if len(row) > 3 else ""
            addr = row[4].strip() if len(row) > 4 else ""
            ptype = row[5].strip() if len(row) > 5 else ""
            lvisit = row[6].strip() if len(row) > 6 else ""
            vcount = row[7].strip() if len(row) > 7 else ""

            # Update current payer if this row has a payer header
            if pay:
                current_payer = pay

            # Parse patient ID and name
            patient_id, patient_name = self.parse_patient_id_name(pid_name)

            # Parse phone number and type
            phone_number, phone_type_parsed = self.parse_phone_with_type(ptype)

            # Skip rows that don't have patient data
            if not patient_name or not patient_id:
                continue

            # Skip patients without insurance
            if current_payer == "Patients Without Insurance":
                continue

            # Initialize patient record if not exists
            if patient_id not in patients:
                patients[patient_id] = {
                    "patient_name": self.text_cleaner.clean_text(patient_name),
                    "address": self.text_cleaner.clean_text(addr),
                    "phone_number": phone_number,
                    "phone_type": phone_type_parsed,
                    "last_visit": lvisit,
                    "visit_count": vcount,
                    "payers": []
                }

            # Add payer info
            patients[patient_id]["payers"].append((current_payer, mid))

            # Update visit info if higher count or later visit
            try:
                current_count = int(vcount) if vcount.isdigit() else 0
                existing_count = int(patients[patient_id]["visit_count"]) if patients[patient_id]["visit_count"].isdigit() else 0
                if current_count > existing_count:
                    patients[patient_id]["visit_count"] = vcount
                    patients[patient_id]["last_visit"] = lvisit
            except ValueError:
                pass

        # Now create records, assigning payers in order
        records = []
        for pid, data in patients.items():
            record = {
                "patient_id": pid,
                "patient_name": data["patient_name"],
                "address": data["address"],
                "phone_number": data["phone_number"],
                "phone_type": data["phone_type"],
                "last_visit": data["last_visit"],
                "visit_count": data["visit_count"],
                "payer_name_p": "",
                "member_id_p": "",
                "payer_name_s": "",
                "member_id_s": "",
                "payer_name_t": "",
                "member_id_t": ""
            }

            # Assign payers
            for i, (payer_name, member_id) in enumerate(data["payers"][:3]):  # Up to 3
                if i == 0:
                    record["payer_name_p"] = payer_name
                    record["member_id_p"] = member_id
                elif i == 1:
                    record["payer_name_s"] = payer_name
                    record["member_id_s"] = member_id
                elif i == 2:
                    record["payer_name_t"] = payer_name
                    record["member_id_t"] = member_id

            records.append(record)

        # Write to CSV
        self._write_csv(records)
        return len(records)

    def _write_csv(self, records: List[Dict]) -> None:
        """Write records to CSV file."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        fieldnames = [
            "patient_id", "patient_name", "address", "phone_number",
            "phone_type", "last_visit", "visit_count", "payer_name_p", "member_id_p",
            "payer_name_s", "member_id_s", "payer_name_t", "member_id_t"
        ]

        with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)


class PatientsDataCleaner:
    """Class for cleaning patients by diagnosis data from Excel files."""

    def __init__(self, input_path: str, output_path: str, service_by_provider_path: Optional[str] = None):
        self.input_path = input_path
        self.output_path = output_path
        self.service_by_provider_path = service_by_provider_path
        self.text_cleaner = TextCleaner()

    def _build_provider_lookup(self) -> Dict[str, str]:
        """Build lookup of normalized (name|dob) to billing provider."""
        if not self.service_by_provider_path or not os.path.exists(self.service_by_provider_path):
            return {}

        rows = ExcelReader.read_excel_rows(self.service_by_provider_path, start_row=0)
        provider_lookup: Dict[str, str] = {}

        header_idx = None
        name_idx = None
        dob_idx = None
        provider_idx = None

        for idx, row in enumerate(rows):
            lower_row = [cell.strip().lower() for cell in row]
            if "patient" in lower_row and "birthdate" in lower_row:
                header_idx = idx
                name_idx = lower_row.index("patient")
                dob_idx = lower_row.index("birthdate")
                if "billing provider" in lower_row:
                    provider_idx = lower_row.index("billing provider")
                break

        if header_idx is None:
            header_idx = -1
            name_idx = 0
            dob_idx = 1
            provider_idx = 2

        current_name = ""
        current_dob = ""

        for row in rows[header_idx + 1:]:
            if provider_idx is None or max(name_idx, dob_idx, provider_idx) >= len(row):
                continue

            name_cell = row[name_idx].strip() if len(row) > name_idx else ""
            dob_cell = row[dob_idx].strip() if len(row) > dob_idx else ""
            provider_cell = row[provider_idx].strip() if len(row) > provider_idx else ""

            if name_cell:
                current_name = name_cell
            if dob_cell:
                current_dob = dob_cell

            if not current_name or not current_dob or not provider_cell:
                continue

            name_key = self.text_cleaner.normalize_name_key(current_name)
            dob_key = self.text_cleaner.normalize_date_key(current_dob)
            if not name_key or not dob_key:
                continue

            lookup_key = f"{name_key}|{dob_key}"
            if lookup_key not in provider_lookup:
                provider_lookup[lookup_key] = provider_cell

        return provider_lookup

    def parse_diagnosis(self, cell: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract ICD code and diagnosis description."""
        if not cell:
            return None, None

        # Expected format: "E11.59-Type 2 diabetes mellitus with other circulatory complication..."
        parts = cell.split("-", 1)
        icd = parts[0].strip() if parts else None
        desc = parts[1].strip() if len(parts) > 1 else None
        return icd, desc

    def clean_data(self) -> int:
        """Clean patients data and return number of records processed."""
        # Read all Excel data
        rows = ExcelReader.read_excel_rows(self.input_path, start_row=0)

        provider_lookup = self._build_provider_lookup()

        records = []
        current_icd = None
        current_diagnosis = None

        for row in rows:
            if len(row) < 8:  # Skip incomplete rows
                continue

            # Check if this is a diagnosis header row (first column has value)
            diagnosis_cell = row[0].strip() if len(row) > 0 else ""
            if diagnosis_cell:
                icd, desc = self.parse_diagnosis(diagnosis_cell)
                if icd:
                    current_icd = icd
                    current_diagnosis = desc
                continue  # Move to next row after updating diagnosis context

            # Check if this is a patient data row (third column has value)
            patient_cell = row[2].strip() if len(row) > 2 else ""
            if patient_cell:
                # Split patient ID and name (format: "91620/ Moore,Chelcy A")
                pid_name = patient_cell.split("/", 1)
                patient_id = pid_name[0].strip() if len(pid_name) > 0 else ""
                name = pid_name[1].strip() if len(pid_name) > 1 else ""

                visit_date = row[3].strip() if len(row) > 3 else ""
                address = row[4].strip() if len(row) > 4 else ""
                phone = row[5].strip() if len(row) > 5 else ""
                dob = row[6].strip() if len(row) > 6 else ""
                email = row[7].strip() if len(row) > 7 else ""

                provider_key = f"{self.text_cleaner.normalize_name_key(name)}|{self.text_cleaner.normalize_date_key(dob)}"
                provider_data = provider_lookup.get(provider_key, "")

                records.append({
                    "patient_id": patient_id,
                    "name": self.text_cleaner.clean_text(name),
                    "address": self.text_cleaner.clean_text(address),
                    "phone": self.text_cleaner.normalize_phone(phone),
                    "dob": dob,
                    "email": email,
                    "last_visit_date": visit_date,
                    "diagnosis": current_diagnosis or "",
                    "icd_code": current_icd or "",
                    "provider_data": provider_data
                })

        # Write to CSV
        self._write_csv(records)
        return len(records)

    def _write_csv(self, records: List[Dict]) -> None:
        """Write records to CSV file."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        fieldnames = [
            "patient_id", "name", "address", "phone", "dob", "email",
            "last_visit_date", "diagnosis", "icd_code", "provider_data"
        ]

        with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)


class PatientListCleaner:
    """Class for cleaning patient list data from Excel files."""

    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.text_cleaner = TextCleaner()

    def clean_data(self) -> int:
        """Clean patient list data and return number of records processed."""
        # Read Excel data starting from row 1 (headers are in row 1, data starts from row 2)
        rows = ExcelReader.read_excel_rows(self.input_path, start_row=1)

        records = []

        for row in rows:
            if len(row) < 25:  # Skip incomplete rows
                continue

            # Extract fields by correct column index (0-based)
            patient_id = row[2].strip() if len(row) > 2 else ""  # Column 3: ID
            patient_name = row[3].strip() if len(row) > 3 else ""  # Column 4: Name
            address_1 = row[14].strip() if len(row) > 14 else ""  # Column 15: Address1
            address_2 = row[15].strip() if len(row) > 15 else ""  # Column 16: Address2
            city = row[16].strip() if len(row) > 16 else ""  # Column 17: City
            state = row[17].strip() if len(row) > 17 else ""  # Column 18: State
            zip_code = row[18].strip() if len(row) > 18 else ""  # Column 19: ZIP
            dob = row[7].strip() if len(row) > 7 else ""  # Column 8: Birth Date
            notes = row[20].strip() if len(row) > 20 else ""  # Column 21: Notes (emergency contact)

            # Skip rows that don't have patient data
            if not patient_id or not patient_name:
                continue

            # Parse emergency contact from notes
            emergency_data = self._parse_emergency_contact(notes)

            records.append({
                "patient_id": patient_id,
                "patient_name": self.text_cleaner.clean_text(patient_name),
                "address": self.text_cleaner.clean_text(", ".join(filter(None, [address_2, address_1]))),  # Street address only
                "city": self.text_cleaner.clean_text(city),
                "state": self.text_cleaner.clean_text(state),
                "zip": self.text_cleaner.clean_text(zip_code),
                "dob": dob,
                "emergency_contact": emergency_data.get('name', ''),
                "emergency_contact_number": emergency_data.get('number', '')
            })

        # Write to CSV
        self._write_csv(records)
        return len(records)

    def _parse_emergency_contact(self, contact_text: str) -> Dict[str, str]:
        """Parse emergency contact information from text into separate fields."""
        if not contact_text:
            return {"name": "", "number": ""}

        # Split into lines and clean up
        lines = [line.strip() for line in contact_text.split('\n') if line.strip()]
        
        # Remove PSPA date lines (format: PSPA MM/DD/YYYY)
        lines = [line for line in lines if not re.match(r'^PSPA \d{2}/\d{2}/\d{4}$', line)]
        
        # Remove other metadata lines
        metadata_patterns = [
            r'^\d{2}\.\d{2}\.\d{4}',  # Date formats like 06.11.2024
            r'^NO EMAIL',  # No email indicators
            r'^MAILED ONLY',  # Mailed statements
            r'.*MEDICAID.*',  # Medicaid notes
            r'.*GHC PORTAL.*',  # Portal references
            r'.*CELL$',  # Incomplete cell references
        ]
        filtered_lines = []
        for line in lines:
            if not any(re.search(pattern, line, re.IGNORECASE) for pattern in metadata_patterns):
                filtered_lines.append(line)
        
        lines = filtered_lines
        
        # Skip if no lines left
        if not lines:
            return {"name": "", "number": ""}
        
        # Check for generic entries that aren't actual contacts
        combined_text = ' '.join(lines).lower()
        generic_entries = [
            "pspa", "emergency contact in file", "no email", "er contact",
            "employee emergency contact in file", "did not provide one",
            "pt is getting her new id", "patient's name on id is",
            "insurance only per office", "no email per patient",
            "no email per pt", "**dr william back**", "none",
            "er contact none", "no email in ghc portal"
        ]
        
        if any(generic.lower() in combined_text for generic in generic_entries):
            return {"name": "", "number": ""}
        
        # Process remaining lines to extract contact info
        contacts = []
        for line in lines:
            # Remove ER contact prefixes
            line = re.sub(r'^(ER|Er)\s+(Contact|Contacts?|contact)[-\s]*', '', line, flags=re.IGNORECASE)
            
            # Look for name and phone patterns
            # Pattern: Name (relationship) phone
            match = re.search(r'([A-Za-z\s]+?)\s*\(([^)]+)\)\s*[\(\d]', line)
            if match:
                name = match.group(1).strip()
                phone_match = re.search(r'[\(\d][\d\s\(\)\-\.]{9,}', line[match.end()-1:])
                if phone_match:
                    phone = self.text_cleaner.normalize_phone(phone_match.group().strip())
                    if phone:
                        contacts.append((name, phone))
                        continue
            
            # Pattern: Name relationship phone
            match = re.search(r'([A-Za-z\s]+?)\s+(mother|father|daughter|son|sister|brother|wife|husband|friend|aunt|uncle|cousin)\s+[\(\d]', line, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                phone_match = re.search(r'[\(\d][\d\s\(\)\-\.]{9,}', line[match.end()-1:])
                if phone_match:
                    phone = self.text_cleaner.normalize_phone(phone_match.group().strip())
                    if phone:
                        contacts.append((name, phone))
                        continue
            
            # Pattern: Name phone (no relationship)
            match = re.search(r'([A-Za-z\s]+?)\s+[\(\d]', line)
            if match and len(match.group(1).strip()) > 2:  # Avoid short names
                name = match.group(1).strip()
                phone_match = re.search(r'[\(\d][\d\s\(\)\-\.]{9,}', line[match.end()-1:])
                if phone_match:
                    phone = self.text_cleaner.normalize_phone(phone_match.group().strip())
                    if phone:
                        contacts.append((name, phone))
                        continue
        
        # If we found contacts, return the first one (primary emergency contact)
        if contacts:
            return {"name": contacts[0][0], "number": contacts[0][1]}
        
        # If no structured contacts found but line looks like a name/phone, try simpler extraction
        for line in lines:
            if re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', line):  # Has phone
                # Extract name as everything before the phone
                phone_match = re.search(r'[\(\d][\d\s\(\)\-\.]{9,}', line)
                if phone_match:
                    name_part = line[:phone_match.start()].strip()
                    phone = self.text_cleaner.normalize_phone(phone_match.group().strip())
                    if phone and name_part and len(name_part) > 2:
                        return {"name": name_part, "number": phone}
        
        return {"name": "", "number": ""}

    def _write_csv(self, records: List[Dict]) -> None:
        """Write records to CSV file."""
    def _write_csv(self, records: List[Dict]) -> None:
        """Write records to CSV file."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        fieldnames = [
            "patient_id", "patient_name", "address", "city", "state", "zip", "dob",
            "emergency_contact", "emergency_contact_number"
        ]

        with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)


class AppointmentsDataCleaner:
    """Class for cleaning appointments data from Excel files."""

    def __init__(self, input_path: str, output_path: str):
        self.input_path = input_path
        self.output_path = output_path
        self.text_cleaner = TextCleaner()

    def parse_patient_info(self, patient_raw: str) -> Tuple[str, str]:
        """Parse patient name and phone from format like 'Abbas, Alan/(313)674-7171'."""
        if not patient_raw or "/" not in patient_raw:
            return "", ""
        
        parts = patient_raw.split("/", 1)
        if len(parts) == 2:
            name = parts[0].strip()
            phone = self.text_cleaner.normalize_phone(parts[1].strip())
            return name, phone
        return patient_raw.strip(), ""

    def parse_datetime(self, datetime_raw: str) -> str:
        """Parse and normalize date/time."""
        if not datetime_raw:
            return ""
        # Clean up and return as is for now
        return datetime_raw.strip()

    def parse_dob(self, dob_raw: str) -> str:
        """Parse and normalize DOB."""
        if not dob_raw:
            return ""
        # Remove time part if present
        dob = dob_raw.split()[0] if " " in dob_raw else dob_raw
        # Convert YYYY-MM-DD to MM/DD/YYYY
        if "-" in dob:
            parts = dob.split("-")
            if len(parts) == 3:
                return f"{parts[1]}/{parts[2]}/{parts[0]}"
        return dob.strip()

    def clean_data(self) -> int:
        """Clean appointments data and return number of records processed."""
        from datetime import datetime
        
        # Read Excel data starting from row 13 (header at index 12)
        rows = ExcelReader.read_excel_rows(self.input_path, start_row=13)

        current_date = datetime.now().date()
        patient_appointments = {}  # key: (name_key, dob_key), value: earliest future datetime

        for row in rows:
            if len(row) < 3:  # Skip incomplete rows
                continue

            # Extract fields by column index
            datetime_raw = row[0].strip() if len(row) > 0 else ""
            patient_raw = row[1].strip() if len(row) > 1 else ""
            dob_raw = row[2].strip() if len(row) > 2 else ""

            # Skip rows that don't have appointment data (like reason rows)
            if not datetime_raw or not patient_raw:
                continue

            # Skip if this looks like a reason row
            if datetime_raw.lower().startswith("reason:"):
                continue

            # Parse patient info
            patient_name, phone = self.parse_patient_info(patient_raw)

            # Parse datetime and DOB
            datetime_clean = self.parse_datetime(datetime_raw)
            dob_clean = self.parse_dob(dob_raw)

            # Skip if no valid patient name
            if not patient_name or not datetime_clean:
                continue

            # Parse appointment date
            try:
                # Try to parse the datetime - it might be in MM/DD/YYYY HH:MM AM/PM format
                appt_datetime = datetime.strptime(datetime_clean, "%m/%d/%Y %I:%M %p")
                appt_date = appt_datetime.date()
            except ValueError:
                try:
                    # Try just date format
                    appt_date = datetime.strptime(datetime_clean.split()[0], "%m/%d/%Y").date()
                except ValueError:
                    # Skip if can't parse date
                    continue

            # Skip past appointments
            if appt_date < current_date:
                continue

            # Create lookup key
            name_key = self.text_cleaner.normalize_name_key(patient_name)
            dob_key = self.text_cleaner.normalize_date_key(dob_clean)
            lookup_key = (name_key, dob_key)

            # Keep the earliest future appointment for each patient
            if lookup_key not in patient_appointments or appt_datetime < patient_appointments[lookup_key][0]:
                patient_appointments[lookup_key] = (appt_datetime, patient_name, phone, dob_clean, datetime_clean)

        # Convert to records
        records = []
        for (name_key, dob_key), (appt_datetime, patient_name, phone, dob_clean, datetime_clean) in patient_appointments.items():
            records.append({
                "patient_name": self.text_cleaner.clean_text(patient_name),
                "phone": phone,
                "dob": dob_clean,
                "datetime": datetime_clean
            })

        # Write to CSV
        self._write_csv(records)
        return len(records)

    def _write_csv(self, records: List[Dict]) -> None:
        """Write records to CSV file."""
        output_dir = os.path.dirname(self.output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        fieldnames = ["patient_name", "phone", "dob", "datetime"]

        with open(self.output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)