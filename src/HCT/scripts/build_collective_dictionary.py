#!/usr/bin/env python3
"""
Build a collective cardiology dictionary for HCT by combining:
- Existing unique disease mapping JSON files across folders
- Hardcoded script dictionaries across folders
- HCT ICD cleaned CSV diagnosis descriptions
- HCT in-script description keywords

Output:
- Temporary file in src/HCT/cleaned (auto-deleted by default)
"""

from __future__ import annotations

import ast
import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from clean_icd_codes import COMORBIDITY_COLUMNS, DESCRIPTION_KEYWORDS


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def normalize_phrase(text: str) -> str:
    return " ".join(clean_text(text).lower().split())


def list_dictionary_files(repo_root: Path) -> list[Path]:
    return sorted(repo_root.glob("src/**/unique_diseases_mapping.json"))


def list_script_files(repo_root: Path) -> list[Path]:
    return sorted(repo_root.glob("src/**/scripts/*.py"))


def read_python_assignments(script_path: Path) -> dict[str, object]:
    assignments: dict[str, object] = {}
    try:
        content = script_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
    except Exception:
        return assignments

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        name = node.targets[0].id
        try:
            assignments[name] = ast.literal_eval(node.value)
        except Exception:
            continue
    return assignments


def merge_hardcoded_script_dictionaries(repo_root: Path, collective: dict[str, set[str]], source_files: list[str]) -> None:
    for script_file in list_script_files(repo_root):
        assignments = read_python_assignments(script_file)
        if not assignments:
            continue

        relative = str(script_file.relative_to(repo_root)).replace("\\", "/")
        used = False

        cause_map = assignments.get("CAUSE_TO_COMORBIDITY")
        if isinstance(cause_map, dict):
            for phrase, comorbidity in cause_map.items():
                p = normalize_phrase(phrase)
                c = clean_text(comorbidity).upper()
                if p and c in collective:
                    collective[c].add(p)
                    used = True

        desc_map = assignments.get("DESCRIPTION_KEYWORDS")
        if isinstance(desc_map, dict):
            for comorbidity, keywords in desc_map.items():
                c = clean_text(comorbidity).upper()
                if c not in collective or not isinstance(keywords, list):
                    continue
                for keyword in keywords:
                    p = normalize_phrase(keyword)
                    if p:
                        collective[c].add(p)
                        used = True

        if used:
            source_files.append(relative)


def parse_cleaned_descriptions(cleaned_csv: Path) -> list[str]:
    df = pd.read_csv(cleaned_csv, dtype=str).fillna("")
    phrases: list[str] = []

    if "ICD CODE DESCRIPTIONS" not in df.columns:
        return phrases

    for joined in df["ICD CODE DESCRIPTIONS"].astype(str):
        if not joined.strip():
            continue
        # Descriptions were exported as comma-separated values.
        for part in joined.split(","):
            phrase = normalize_phrase(part)
            if phrase:
                phrases.append(phrase)

    return phrases


def build_collective_dictionary(repo_root: Path, hct_base: Path) -> Path:
    cleaned_dir = hct_base / "cleaned"
    cleaned_dir.mkdir(parents=True, exist_ok=True)

    # Initialize dictionary with baseline keyword lists from HCT ICD script.
    collective: dict[str, set[str]] = {
        comorbidity: {normalize_phrase(k) for k in DESCRIPTION_KEYWORDS.get(comorbidity, []) if normalize_phrase(k)}
        for comorbidity in COMORBIDITY_COLUMNS
    }

    source_files: list[str] = []

    # Merge unique disease mapping JSON files from all folders.
    for json_file in list_dictionary_files(repo_root):
        source_files.append(str(json_file.relative_to(repo_root)).replace("\\", "/"))
        with open(json_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        for phrase, comorbidity in mapping.items():
            c = clean_text(comorbidity).upper()
            p = normalize_phrase(phrase)
            if not p:
                continue
            if c in collective:
                collective[c].add(p)

    # Merge hardcoded dictionaries directly from scripts in all folders.
    merge_hardcoded_script_dictionaries(repo_root, collective, source_files)

    # Merge phrase evidence from latest HCT cleaned ICD output.
    cleaned_files = sorted((hct_base / "cleaned").glob("patient-icd-codes-cleaned-*.csv"))
    if cleaned_files:
        latest_cleaned = cleaned_files[-1]
        source_files.append(str(latest_cleaned.relative_to(repo_root)).replace("\\", "/"))
        phrase_counts = defaultdict(int)
        description_phrases = parse_cleaned_descriptions(latest_cleaned)
        for p in description_phrases:
            phrase_counts[p] += 1

        # Auto-assign phrases to comorbidities by keyword presence.
        for phrase, count in phrase_counts.items():
            if count < 2:
                continue
            for comorbidity, keywords in DESCRIPTION_KEYWORDS.items():
                if any(k in phrase for k in keywords):
                    collective[comorbidity].add(phrase)
                    break

    output_payload = {
        "generated_at": datetime.now().isoformat(),
        "comorbidity_columns": COMORBIDITY_COLUMNS,
        "sources": source_files,
        "dictionary": {
            comorbidity: sorted(list(values))
            for comorbidity, values in collective.items()
        },
    }

    output_file = cleaned_dir / "hct_collective_dictionary_tmp.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2)

    return output_file


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep-temp", action="store_true", help="Keep the temporary dictionary file in cleaned folder")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    hct_base = Path(__file__).resolve().parents[1]
    out = build_collective_dictionary(repo_root, hct_base)
    with open(out, "r", encoding="utf-8") as f:
        payload = json.load(f)

    print(f"Temporary dictionary created: {out}")
    print(f"Sources scanned: {len(payload.get('sources', []))}")
    for comorbidity, entries in payload.get("dictionary", {}).items():
        print(f"{comorbidity}: {len(entries)}")

    if not args.keep_temp:
        out.unlink(missing_ok=True)
        print(f"Temporary dictionary deleted: {out}")


if __name__ == "__main__":
    main()
