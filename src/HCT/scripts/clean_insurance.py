#!/usr/bin/env python3
"""
Clean HCT insurance data and map it to consolidated-view insurance columns.

Output:
- src/HCT/cleaned/patient-insurance-cleaned-<timestamp>.csv
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


def clean_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def clean_emr_id_as_text(value: object) -> str:
    """
    Keep EMR ID as text even when input looks numeric.
    """
    text = clean_text(value)
    if not text:
        return ""

    # Per Nbr can contain suffixes; keep leading numeric id when present.
    match = re.match(r"\s*(\d+)", text)
    if match:
        return match.group(1)
    return text


def normalize_cob(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""

    match = re.search(r"[123]", text)
    return match.group(0) if match else ""


def is_invalid_report_row(row: pd.Series) -> bool:
    row_text = " ".join(clean_text(v) for v in row.values if clean_text(v))
    if not row_text:
        return False

    lowered = row_text.lower()
    return (
        "filters - [filter 1]" in lowered
        or "[columns ]:" in lowered
        or "[report name]:" in lowered
    )


def pick_best_row(group: pd.DataFrame) -> pd.Series:
    """
    Pick first row with usable payer/policy details for a COB level.
    """
    ranked = group.copy()
    ranked["_has_data"] = ranked.apply(
        lambda r: 1 if clean_text(r.get("Payer Name", "")) or clean_text(r.get("Pol Nbr", "")) else 0,
        axis=1,
    )
    ranked = ranked.sort_values(by=["_has_data"], ascending=[False])
    return ranked.iloc[0]


def aggregate_insurance(source: pd.DataFrame) -> pd.DataFrame:
    work = source.copy()

    work = work[~work.apply(is_invalid_report_row, axis=1)].copy()
    work["_emr_id"] = work.get("Per Nbr", "").map(clean_emr_id_as_text)
    work = work[work["_emr_id"] != ""].copy()

    work["_enc_cob"] = work.get("Enc Cob", "").map(normalize_cob)
    work = work[work["_enc_cob"].isin(["1", "2", "3"])].copy()

    output_rows: list[dict[str, str]] = []
    cob_to_prefix = {
        "1": "PRIMARY",
        "2": "SECONDARY",
        "3": "TERITARY",
    }

    for emr_id, patient_group in work.groupby("_emr_id", sort=False):
        row_out: dict[str, str] = {
            "EMR ID": emr_id,
            "PRIMARY INSURANCE": "",
            "PRIMARY ID": "",
            "PRIMARY GROUP": "",
            "SECONDARY INSURANCE": "",
            "SECONDARY ID": "",
            "SECONDARY GROUP": "",
            "TERITARY INSURANCE": "",
            "TERITARY ID": "",
            "TERITARY GROUP": "",
            "INSURANCE TYPE": "",
            "CO-PAY": "",
            "MEDICARE ID": "",
        }

        primary_ins_type = ""

        for cob_value, prefix in cob_to_prefix.items():
            cob_group = patient_group[patient_group["_enc_cob"] == cob_value]
            if cob_group.empty:
                continue

            best = pick_best_row(cob_group)
            row_out[f"{prefix} INSURANCE"] = clean_text(best.get("Payer Name", ""))
            row_out[f"{prefix} ID"] = clean_text(best.get("Pol Nbr", ""))
            row_out[f"{prefix} GROUP"] = clean_text(best.get("Group Name", ""))

            if cob_value == "1":
                primary_ins_type = clean_text(best.get("Ins Type", ""))
                row_out["INSURANCE TYPE"] = primary_ins_type
                row_out["CO-PAY"] = clean_text(best.get("Co Amt", ""))

        primary_ins_name = row_out.get("PRIMARY INSURANCE", "").lower()
        if "medicare" in primary_ins_name or "medicare" in primary_ins_type.lower():
            row_out["MEDICARE ID"] = row_out.get("PRIMARY ID", "")

        output_rows.append(row_out)

    return pd.DataFrame(output_rows)


def transform_insurance(input_file: Path, template_file: Path, output_dir: Path) -> Path:
    # HCT insurance headers start on row 5 -> zero-based header index 4.
    source = pd.read_excel(input_file, header=4)
    template_headers = list(pd.read_excel(template_file, nrows=0).columns)

    aggregated = aggregate_insurance(source)

    # Do not touch demographics-filled columns: only populate insurance-owned fields + EMR ID.
    output = pd.DataFrame("", index=aggregated.index, columns=template_headers)
    insurance_columns = [
        "EMR ID",
        "PRIMARY INSURANCE",
        "PRIMARY ID",
        "PRIMARY GROUP",
        "SECONDARY INSURANCE",
        "SECONDARY ID",
        "SECONDARY GROUP",
        "TERITARY INSURANCE",
        "TERITARY ID",
        "TERITARY GROUP",
        "INSURANCE TYPE",
        "CO-PAY",
        "MEDICARE ID",
    ]

    for col in insurance_columns:
        if col in output.columns and col in aggregated.columns:
            output[col] = aggregated[col].map(clean_text)

    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"patient-insurance-cleaned-{timestamp}.csv"
    output.to_csv(output_file, index=False, encoding="utf-8-sig")
    return output_file


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Clean HCT patient insurance into consolidated-view insurance columns.")
    parser.add_argument(
        "--input",
        default=str(base_dir / "patient-insurance.xlsx"),
        help="Path to patient insurance Excel file",
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

    output_file = transform_insurance(
        input_file=Path(args.input),
        template_file=Path(args.template),
        output_dir=Path(args.output_dir),
    )

    print(f"Created: {output_file}")


if __name__ == "__main__":
    main()
