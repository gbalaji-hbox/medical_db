#!/usr/bin/env python3
"""
Clean HCT demographics data and map it to consolidated view template columns.

Output:
- src/HCT/cleaned/patient-demographics-cleaned-<timestamp>.csv
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


ALLOWED_CITY_KEYWORDS = {
    "fort worth",
    "granbury",
    "weatherford",
}


def clean_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def clean_emr_id(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""
    match = re.match(r"\s*(\d+)", text)
    if match:
        return match.group(1)
    return text


def split_patient_name(name: object) -> tuple[str, str, str, str]:
    """
    Parse 'Last, First Middle' into components.
    Returns first_name, middle_name, last_name, full_name.
    """
    raw = clean_text(name)
    if not raw:
        return "", "", "", ""

    if "," in raw:
        last, right = raw.split(",", 1)
        last_name = clean_text(last)
        right_tokens = [t for t in clean_text(right).split() if t]
        first_name = right_tokens[0] if right_tokens else ""
        middle_name = " ".join(right_tokens[1:]) if len(right_tokens) > 1 else ""
    else:
        tokens = [t for t in raw.split() if t]
        first_name = tokens[0] if tokens else ""
        last_name = tokens[-1] if len(tokens) > 1 else ""
        middle_name = " ".join(tokens[1:-1]) if len(tokens) > 2 else ""

    full_name = " ".join(part for part in [first_name, middle_name, last_name] if part)
    return first_name, middle_name, last_name, full_name


def clean_provider_name(name: object) -> str:
    """
    Convert 'Last, First Middle' to 'First Middle Last'.
    """
    raw = clean_text(name)
    if not raw:
        return ""

    if "," in raw:
        last, right = raw.split(",", 1)
        last_name = clean_text(last)
        first_middle = clean_text(right)
        return " ".join(part for part in [first_middle, last_name] if part)

    return " ".join(raw.split())


def format_date_mm_dd_yyyy(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""

    dt = pd.to_datetime(text, errors="coerce")
    if pd.isna(dt):
        return ""
    return dt.strftime("%m-%d-%Y")


def build_street_address(addr2: object, addr1: object) -> str:
    # Required order from user: Addr 2 + Addr 1, separated by comma.
    # Skip addr2 if it is already a substring of addr1 (case-insensitive).
    a2 = clean_text(addr2)
    a1 = clean_text(addr1)
    if a2 and a1 and a2.lower() in a1.lower():
        return a1
    return ", ".join(part for part in [a2, a1] if part)


def normalize_location(value: object) -> str:
    return " ".join(clean_text(value).lower().split())


def is_allowed_encounter_location(value: object) -> bool:
    """
    Allow short/expanded variants for Heart Ctr of North TX locations,
    limited to Fort Worth, Granbury, and Weatherford.
    """
    location = normalize_location(value)
    if not location:
        return False

    has_heart = "heart" in location
    has_center_keyword = ("ctr" in location) or ("center" in location)
    has_north_tx = (
        ("n tx" in location)
        or ("north tx" in location)
        or ("north texas" in location)
    )
    has_allowed_city = any(city in location for city in ALLOWED_CITY_KEYWORDS)

    return has_heart and has_center_keyword and has_north_tx and has_allowed_city


def is_invalid_report_row(row: pd.Series) -> bool:
    """
    Remove exported report-metadata rows that can appear inside data.
    """
    row_text = " ".join(clean_text(v) for v in row.values if clean_text(v))
    if not row_text:
        return False

    lowered = row_text.lower()
    return (
        "filters - [filter 1]" in lowered
        or "[report name]: hbox-demographics-new" in lowered
        or "[columns ]:" in lowered
    )


def deduplicate_source(source: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate patients caused by provider-level repeats.
    Keep the first row with non-empty Provider Name for each patient key.
    """
    work = source.copy()

    work = work[~work.apply(is_invalid_report_row, axis=1)].copy()
    work = work[work.get("Lst Enc Loc Name", "").map(is_allowed_encounter_location)].copy()

    work["_emr_key"] = work.get("Per Nbr", "").map(clean_emr_id)
    work["_name_key"] = work.get("Pat Name", "").map(lambda v: clean_text(v).lower())
    work["_dob_key"] = work.get("Birth Dt", "").map(format_date_mm_dd_yyyy)
    work["_dedupe_key"] = work.apply(
        lambda r: (
            r["_emr_key"]
            if clean_text(r["_emr_key"])
            else "|".join([r["_name_key"], r["_dob_key"]])
        ),
        axis=1,
    )
    work["_provider_has_value"] = work.get("Rendering", "").map(
        lambda v: 1 if clean_text(v) else 0
    )

    work = work.sort_values(by=["_dedupe_key", "_provider_has_value"], ascending=[True, False])
    work = work.drop_duplicates(subset=["_dedupe_key"], keep="first")

    return work.drop(
        columns=["_emr_key", "_name_key", "_dob_key", "_dedupe_key", "_provider_has_value"],
        errors="ignore",
    ).reset_index(drop=True)


def transform_demographics(input_file: Path, template_file: Path, output_dir: Path) -> Path:
    # HCT demographics headers start on row 5 -> zero-based header index 4.
    source = pd.read_excel(input_file, header=4)
    source = deduplicate_source(source)
    template_headers = list(pd.read_excel(template_file, nrows=0).columns)

    output = pd.DataFrame("", index=source.index, columns=template_headers)

    output["EMR ID"] = source.get("Per Nbr", "").map(clean_emr_id)
    output["PATIENT EMR NAME"] = source.get("Pat Name", "").map(clean_text)

    parsed_names = source.get("Pat Name", "").map(split_patient_name)
    output["FIRST NAME"] = parsed_names.map(lambda x: x[0])
    output["MIDDLE NAME"] = parsed_names.map(lambda x: x[1])
    output["LAST NAME"] = parsed_names.map(lambda x: x[2])
    output["PATIENT FULL NAME"] = parsed_names.map(lambda x: x[3])

    output["DATE OF BIRTH"] = source.get("Birth Dt", "").map(format_date_mm_dd_yyyy)
    output["GENDER"] = source.get("Sex", "").map(clean_text)
    output["STREET ADDRESS"] = [
        build_street_address(a2, a1)
        for a2, a1 in zip(source.get("Addr 2", ""), source.get("Addr 1", ""))
    ]
    output["CITY"] = source.get("City", "").map(clean_text)
    output["STATE"] = source.get("State", "").map(clean_text)
    output["ZIP"] = source.get("Zip", "").map(clean_text)

    output["HOME PHONE"] = source.get("Hm Phone", "").map(clean_text)
    output["MOBILE PHONE"] = source.get("Cell Phone", "").map(clean_text)
    output["WORK PHONE"] = source.get("Day Phone", "").map(clean_text)
    output["EMAIL ADDRESS"] = source.get("Email Addr", "").map(clean_text)
    output["LANGUAGE"] = source.get("Preferred Language", "").map(clean_text)
    output["RACE"] = source.get("Race", "").map(clean_text)

    output["LAST SEEN DATE"] = source.get("Lst Enc Dt", "").map(format_date_mm_dd_yyyy)
    output["NEXT APPT"] = source.get("Nxt Appt Dt", "").map(format_date_mm_dd_yyyy)

    output["PROVIDER DATA"] = source.get("Rendering", "").map(clean_text)
    output["PROVIDER NAME"] = source.get("Rendering", "").map(clean_provider_name)
    output["CLINIC FACILITY"] = source.get("Lst Enc Loc Name", "").map(clean_text)
    output["PRIMARY CARE PROVIDER"] = source.get("Prim Care Phys", "").map(clean_text)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"patient-demographics-cleaned-{timestamp}.csv"
    output.to_csv(output_file, index=False, encoding="utf-8-sig")

    return output_file


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Clean HCT patient demographics into consolidated-view schema.")
    parser.add_argument(
        "--input",
        default=str(base_dir / "patient-demographics.xlsx"),
        help="Path to patient demographics Excel file",
    )
    parser.add_argument(
        "--template",
        default=str(base_dir / "template" / "consolidated_view-template - new.xlsx"),
        help="Path to consolidated view template Excel file",
    )
    parser.add_argument(
        "--output-dir",
        default=str(base_dir / "cleaned"),
        help="Directory where cleaned CSV will be written",
    )

    args = parser.parse_args()

    output_file = transform_demographics(
        input_file=Path(args.input),
        template_file=Path(args.template),
        output_dir=Path(args.output_dir),
    )

    print(f"Created: {output_file}")


if __name__ == "__main__":
    main()
