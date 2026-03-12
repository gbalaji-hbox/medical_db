import os
import glob
from datetime import datetime
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUTPUT_DIR = os.path.join(ROOT, 'output')

TARGET_NAMES = ['Khambatta', 'Edwards', 'Mesiha']


def find_latest_consolidated():
    pattern = os.path.join(OUTPUT_DIR, 'consolidated_data_new_*.xlsx')
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def main():
    src = find_latest_consolidated()
    if not src:
        print('No consolidated file found in output/; run converter first.')
        return
    df = pd.read_excel(src, sheet_name=0, engine='openpyxl')
    # ensure PROVIDER_NAME exists
    if 'PROVIDER_NAME' not in df.columns:
        print('PROVIDER_NAME column not found in consolidated file.')
        return
    # filter rows where provider last name matches any target
    def matches(name):
        if pd.isna(name):
            return False
        s = str(name).lower()
        for t in TARGET_NAMES:
            if t.lower() in s:
                return True
        return False

    filt = df[df['PROVIDER_NAME'].apply(matches)]
    # produce output with full patient rows for matched providers
    # keep all columns from the consolidated file but only rows matching targets
    out_df = filt.copy()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = os.path.join(OUTPUT_DIR, f'filtered_patients_by_provider_{ts}.xlsx')
    out_df.to_excel(out_path, index=False)
    print('Wrote', out_path)
    # show a small preview
    if len(out_df) == 0:
        print('No rows matched the target providers.')
    else:
        print(out_df.head(20).to_string(index=False))


if __name__ == '__main__':
    main()
