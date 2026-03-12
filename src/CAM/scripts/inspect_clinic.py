import os
import sys
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CIM_ROOT = os.path.join(ROOT, 'CIM')
HBOX = os.path.join(CIM_ROOT, 'Hbox list 3 9 26.xlsx')

def main():
    df = pd.read_excel(HBOX, sheet_name='Sheet1', engine='openpyxl')
    cols = ['Dept/Loc', 'CLINIC FACILITY', 'Clinic Facility']
    found = False
    for col in cols:
        if col in df.columns:
            vals = df[col].dropna().astype(str)
            mask = vals.str.contains('HFCC', case=False, na=False) | vals.str.contains('ROSEVILLE', case=False, na=False)
            sub = vals[mask]
            if not sub.empty:
                print(f"Column: {col} - matches: {len(sub)}")
                print(sub.value_counts().head(20).to_string())
                found = True
    if not found:
        print('No matching clinic facility values found containing HFCC or ROSEVILLE in expected columns.')

if __name__ == '__main__':
    main()
