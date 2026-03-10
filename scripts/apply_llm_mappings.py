import os
import sys
import shutil
import subprocess
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
MAPPINGS_DIR = os.path.join(ROOT, "mappings")
EXISTING = os.path.join(MAPPINGS_DIR, "problem_list_mapping.csv")
LLM = os.path.join(MAPPINGS_DIR, "problem_list_llm_mapping.csv")
BACKUP = os.path.join(MAPPINGS_DIR, "problem_list_mapping.bak.csv")
LOG = os.path.join(MAPPINGS_DIR, "problem_list_llm_integration_log.txt")

def read_csv_if_exists(path, **kwargs):
    if os.path.exists(path):
        return pd.read_csv(path, dtype=str).fillna("")
    return pd.DataFrame()

def main():
    os.makedirs(MAPPINGS_DIR, exist_ok=True)
    df_exist = read_csv_if_exists(EXISTING)
    df_llm = read_csv_if_exists(LLM)

    if df_llm.empty:
        print("No LLM mapping file found at", LLM)
        sys.exit(1)

    # Ensure expected columns
    if df_exist.empty:
        df_exist = pd.DataFrame(columns=["token","matched_cause","icd_code","method","notes"]) 

    df_exist = df_exist.astype(str)
    df_llm = df_llm.astype(str)

    df_exist_indexed = df_exist.set_index("token", drop=False)

    updated = 0
    added = 0
    for _, row in df_llm.iterrows():
        token = row.get("token","").strip()
        suggested = row.get("suggested_cause","").strip()
        icd = row.get("icd_code","").strip()
        notes = row.get("notes","").strip()
        if not token:
            continue
        if not suggested:
            continue

        if token in df_exist_indexed.index:
            existing_cause = df_exist_indexed.at[token, "matched_cause"]
            # Only overwrite if existing mapping is empty
            if not existing_cause:
                df_exist_indexed.at[token, "matched_cause"] = suggested
                df_exist_indexed.at[token, "icd_code"] = icd
                df_exist_indexed.at[token, "method"] = "llm"
                df_exist_indexed.at[token, "notes"] = notes
                updated += 1
        else:
            new = {
                "token": token,
                "matched_cause": suggested,
                "icd_code": icd,
                "method": "llm",
                "notes": notes,
            }
            df_exist_indexed = pd.concat([df_exist_indexed, pd.DataFrame([new]).set_index("token")])
            added += 1

    # Write backup and merged
    if os.path.exists(EXISTING):
        shutil.copy2(EXISTING, BACKUP)

    merged = df_exist_indexed.reset_index(drop=True)
    merged.to_csv(EXISTING, index=False)

    with open(LOG, "w", encoding="utf-8") as f:
        f.write(f"LLM integration run\n")
        f.write(f"LLM file: {LLM}\n")
        f.write(f"Existing mapping: {EXISTING}\n")
        f.write(f"Added: {added}\n")
        f.write(f"Updated: {updated}\n")

    print(f"LLM integration complete. Added={added} Updated={updated}")

    # Re-run converter
    converter = os.path.join(ROOT, "scripts", "convert_to_consolidated.py")
    if os.path.exists(converter):
        print("Running converter...")
        proc = subprocess.run([sys.executable, converter], cwd=ROOT)
        print("Converter exit code:", proc.returncode)
        if proc.returncode != 0:
            print("Converter failed. See above for errors.")
            sys.exit(proc.returncode)
    else:
        print("Converter script not found at", converter)

if __name__ == "__main__":
    main()
