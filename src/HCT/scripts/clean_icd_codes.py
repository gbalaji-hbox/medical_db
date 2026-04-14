#!/usr/bin/env python3
"""
Clean HCT ICD workbook into a simple grouped CSV.

Output:
- src/HCT/cleaned/patient-icd-codes-cleaned-<timestamp>.csv
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


COMORBIDITY_COLUMNS = [
    "CORONARY ARTERY DISEASE",
    "ARRHYTHMIA",
    "CONGESTIVE HEART FAILURE",
    "PERIPHERAL VASCULAR",
    "VALVULAR HEART",
    "CERBOVASCULAR ACCIDENT",
    "HYPERLIPIDEMIA",
    "ANGINA PECTORIS",
    "HYPOTENSION",
    "HYPERTENSION",
    "OBESITY",
    "DIABETES",
    "CHRONIC KIDNEY DISEASE",
    "COPD",
    "RESPIRATORY FAILURE",
    "ASTHMA",
    "SLEEP APNEA",
    "DYSPNEA",
    "EMPHYSEMA",
    "BRONCHIECTASIS",
    "HYPOXEMIA",
]

CAUSE_TO_COMORBIDITY = {
    "Coronary Artery Disease": "CORONARY ARTERY DISEASE",
    "Arrhythmia": "ARRHYTHMIA",
    "CHF (Congestive Heart Failure)": "CONGESTIVE HEART FAILURE",
    "Peripheral Vascular Disease": "PERIPHERAL VASCULAR",
    "Valvular Heart Disease": "VALVULAR HEART",
    "Cerebrovascular Accident": "CERBOVASCULAR ACCIDENT",
    "Hyperlipidemia": "HYPERLIPIDEMIA",
    "Angina Pectoris": "ANGINA PECTORIS",
    "Hypotension": "HYPOTENSION",
    "Hypertension": "HYPERTENSION",
}

PRIMARY_DX_DISALLOWED = {
    "ASTHMA",
    "ANGINA PECTORIS",
    "CHRONIC KIDNEY DISEASE",
    "COPD",
    "DIABETES",
    "DYSPNEA",
    "OBESITY",
    "SLEEP APNEA",
}

DESCRIPTION_KEYWORDS = {
    "CORONARY ARTERY DISEASE": [
        "coronary artery disease",
        "athscl heart disease",
        "atherosclerotic heart disease",
        "ischemic heart",
        "aortocoronary bypass",
    ],
    "ARRHYTHMIA": [
        "arrhythmia",
        "atrial fibrillation",
        "atrial flutter",
        "tachycardia",
        "bradycardia",
        "palpitations",
    ],
    "CONGESTIVE HEART FAILURE": [
        "heart failure",
        "congestive heart failure",
        "systolic heart failure",
        "diastolic heart failure",
    ],
    "PERIPHERAL VASCULAR": [
        "peripheral vascular",
        "peripheral angiopath",
        "venous insufficiency",
    ],
    "VALVULAR HEART": [
        "valve",
        "valvular",
        "mitral",
        "aortic",
        "tricuspid",
        "prosthetic heart valve",
    ],
    "CERBOVASCULAR ACCIDENT": [
        "cerebrovascular",
        "stroke",
        "transient cerebral ischemic",
        "carotid",
    ],
    "HYPERLIPIDEMIA": [
        "hyperlipidemia",
        "hypercholesterolemia",
        "mixed hyperlipidemia",
    ],
    "ANGINA PECTORIS": [
        "angina",
        "precordial pain",
        "chest pain",
    ],
    "HYPOTENSION": [
        "hypotension",
        "orthostatic hypotension",
    ],
    "HYPERTENSION": [
        "hypertension",
        "hypertensive heart disease",
    ],
}


def clean_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def clean_emr_id_as_text(value: object) -> str:
    text = clean_text(value)
    if not text:
        return ""

    match = re.match(r"\s*(\d+)", text)
    if match:
        return match.group(1)
    return text


def unique_join(values: list[str]) -> str:
    seen: set[str] = set()
    out: list[str] = []
    for v in values:
        val = clean_text(v)
        if not val:
            continue
        if val in seen:
            continue
        seen.add(val)
        out.append(val)
    return ", ".join(out)


def normalize_icd(icd: object) -> str:
    """
    Normalize ICD format for stable matching.
    """
    code = clean_text(icd).upper().replace(" ", "")
    return code


def icd_prefix3(icd: object) -> str:
    code = normalize_icd(icd)
    if not code:
        return ""
    code_no_dot = code.replace(".", "")
    return code_no_dot[:3]


def load_api_mappings(api_file: Path) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """
    Build exact ICD and 3-char prefix lookup maps from api_prescription list.
    """
    df = pd.read_csv(api_file)
    exact_to_comorbidity: dict[str, str] = {}
    prefix_to_comorbidity: dict[str, str] = {}
    comorbidity_to_icd: dict[str, str] = {}

    for _, row in df.iterrows():
        cause = clean_text(row.get("cause", ""))
        icd_code = normalize_icd(row.get("icd_code", ""))
        if not cause or not icd_code:
            continue
        if cause not in CAUSE_TO_COMORBIDITY:
            continue

        comorbidity = CAUSE_TO_COMORBIDITY[cause]
        exact_to_comorbidity[icd_code] = comorbidity
        comorbidity_to_icd.setdefault(comorbidity, icd_code)

        prefix = icd_prefix3(icd_code)
        if prefix:
            prefix_to_comorbidity[prefix] = comorbidity

    return exact_to_comorbidity, prefix_to_comorbidity, comorbidity_to_icd


def match_icd_to_comorbidity(
    raw_icd: str,
    exact_to_comorbidity: dict[str, str],
    prefix_to_comorbidity: dict[str, str],
) -> str:
    """
    Match order: exact ICD first, then 3-char prefix.
    """
    norm = normalize_icd(raw_icd)
    if not norm:
        return ""

    if norm in exact_to_comorbidity:
        return exact_to_comorbidity[norm]

    prefix = icd_prefix3(norm)
    return prefix_to_comorbidity.get(prefix, "")


def pick_primary_secondary_dx(yes_comorbidities: list[str]) -> tuple[str, str]:
    primary_dx = ""
    secondary_dx = ""

    for comorb in yes_comorbidities:
        if comorb not in PRIMARY_DX_DISALLOWED:
            primary_dx = comorb
            break

    # If suppression removed all primary candidates, use the first available mapped
    # comorbidity so records do not remain invalid with empty PRIMARY DX.
    if not primary_dx and yes_comorbidities:
        primary_dx = yes_comorbidities[0]

    for comorb in yes_comorbidities:
        if comorb != primary_dx:
            secondary_dx = comorb
            break

    return primary_dx, secondary_dx


def detect_comorbidity_from_description(description: str) -> str:
    desc = clean_text(description).lower()
    if not desc:
        return ""

    for comorbidity, keywords in DESCRIPTION_KEYWORDS.items():
        if any(keyword in desc for keyword in keywords):
            return comorbidity

    return ""


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


def build_grouped_icd(input_file: Path, api_file: Path, template_file: Path, output_dir: Path) -> Path:
    # HCT ICD workbook data headers start on row 5 -> zero-based index 4.
    source = pd.read_excel(input_file, header=4)
    source = source[~source.apply(is_invalid_report_row, axis=1)].copy()

    source["EMR ID"] = source.get("Per Nbr", "").map(clean_emr_id_as_text)
    source["PATIENT EMR NAME"] = source.get("Pat Name", "").map(clean_text)
    source = source[source["EMR ID"] != ""].copy()

    exact_to_comorbidity, prefix_to_comorbidity, comorbidity_to_icd = load_api_mappings(api_file)

    diag_cols = [f"Diag {i}" for i in range(1, 13) if f"Diag {i}" in source.columns]
    desc_cols = [f"Diag {i} Desc" for i in range(1, 13) if f"Diag {i} Desc" in source.columns]

    output_rows: list[dict[str, str]] = []

    for emr_id, group in source.groupby("EMR ID", sort=False):
        patient_name = ""
        codes_accum: list[str] = []
        descs_accum: list[str] = []
        comorbidity_flags = {name: "NO" for name in COMORBIDITY_COLUMNS}
        comorbidity_to_raw_icd: dict[str, str] = {}

        for _, row in group.iterrows():
            if not patient_name:
                patient_name = clean_text(row.get("PATIENT EMR NAME", ""))

            for i in range(1, 13):
                code_col = f"Diag {i}"
                desc_col = f"Diag {i} Desc"

                raw_icd = clean_text(row.get(code_col, "")) if code_col in source.columns else ""
                raw_desc = clean_text(row.get(desc_col, "")) if desc_col in source.columns else ""

                codes_accum.append(raw_icd)
                descs_accum.append(raw_desc)

                matched_comorbidity = match_icd_to_comorbidity(
                    raw_icd,
                    exact_to_comorbidity,
                    prefix_to_comorbidity,
                )
                matched_from_description = False

                # Fallback: derive mapped cardiology comorbidity from diagnosis description.
                if not matched_comorbidity:
                    matched_comorbidity = detect_comorbidity_from_description(raw_desc)
                    matched_from_description = bool(matched_comorbidity)

                if matched_comorbidity:
                    comorbidity_flags[matched_comorbidity] = "YES"
                    if matched_comorbidity not in comorbidity_to_raw_icd:
                        if raw_icd:
                            comorbidity_to_raw_icd[matched_comorbidity] = raw_icd
                        elif matched_from_description:
                            comorbidity_to_raw_icd[matched_comorbidity] = comorbidity_to_icd.get(matched_comorbidity, "")

        yes_comorbidities = [
            name for name in COMORBIDITY_COLUMNS if comorbidity_flags[name] == "YES"
        ]
        primary_dx, secondary_dx = pick_primary_secondary_dx(yes_comorbidities)
        primary_icd = comorbidity_to_raw_icd.get(primary_dx, "") if primary_dx else ""
        secondary_icd = comorbidity_to_raw_icd.get(secondary_dx, "") if secondary_dx else ""

        row_out = {
            "EMR ID": emr_id,
            "PATIENT EMR NAME": patient_name,
            "ICD CODES": unique_join(codes_accum),
            "ICD CODE DESCRIPTIONS": unique_join(descs_accum),
            "PRIMARY DX": primary_dx,
            "SECONDARY DX": secondary_dx,
            "PRIMARY ICD": primary_icd,
            "SECONDARY ICD": secondary_icd,
        }
        row_out.update(comorbidity_flags)
        output_rows.append(row_out)

    output_raw = pd.DataFrame(output_rows)

    # Keep only patients with at least one mapped cardiology comorbidity.
    if not output_raw.empty:
        has_any_yes = output_raw[COMORBIDITY_COLUMNS].eq("YES").any(axis=1)
        output_raw = output_raw[has_any_yes].copy()

    # Safety check: enforce one row per EMR ID.
    output_raw = output_raw.drop_duplicates(subset=["EMR ID"], keep="first")

    # Align export column order to template. Keep ICD aggregate columns at the end.
    template_headers = list(pd.read_excel(template_file, nrows=0).columns)
    output = pd.DataFrame("", index=output_raw.index, columns=template_headers)

    for col in output_raw.columns:
        if col in output.columns:
            output[col] = output_raw[col]

    for extra_col in ["ICD CODES", "ICD CODE DESCRIPTIONS"]:
        if extra_col in output_raw.columns:
            output[extra_col] = output_raw[extra_col]

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"patient-icd-codes-cleaned-{timestamp}.csv"
    output.to_csv(output_file, index=False, encoding="utf-8-sig")
    return output_file


def main() -> None:
    base_dir = Path(__file__).resolve().parents[1]

    parser = argparse.ArgumentParser(description="Group HCT ICD codes by Per Nbr and export a simple CSV.")
    parser.add_argument(
        "--input",
        default=str(base_dir / "HCT_Location Wise_Provider Wise_Patient Wise_ICD Codes.xlsx"),
        help="Path to HCT ICD workbook",
    )
    parser.add_argument(
        "--output-dir",
        default=str(base_dir / "cleaned"),
        help="Output directory for cleaned CSV",
    )
    parser.add_argument(
        "--api-prescription",
        default=str(base_dir / "template" / "api_prescriptioncauselist_202603101243.csv"),
        help="Path to api prescription cause list CSV",
    )
    parser.add_argument(
        "--template",
        default=str(base_dir / "template" / "consolidated_view-template - new.xlsx"),
        help="Path to consolidated view template file for output column order",
    )

    args = parser.parse_args()

    output_file = build_grouped_icd(
        input_file=Path(args.input),
        api_file=Path(args.api_prescription),
        template_file=Path(args.template),
        output_dir=Path(args.output_dir),
    )

    print(f"Created: {output_file}")


if __name__ == "__main__":
    main()
