import os
import sys
import pandas as pd

# ensure module import paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.convert_data_new_to_template import find_problem_matches

DATA_PATH = os.path.join('src', 'CIM', 'data_new.xlsx')
DISEASE_CSV = os.path.join('src', 'CIM', 'disease', 'api_prescriptioncauselist_202603101243.csv')

def load_disease_causes():
    if not os.path.exists(DISEASE_CSV):
        return []
    df = pd.read_csv(DISEASE_CSV)
    return [str(x).strip().lower() for x in df['cause'].fillna('') if str(x).strip()]

def main(mrn=3368928):
    df = pd.read_excel(DATA_PATH, engine='openpyxl')
    row = df[df.get('MRN')==mrn]
    if row.empty:
        print('MRN not found:', mrn)
        return
    r = row.iloc[0]
    pl = r.get('Problem List') or r.get('ProblemList') or r.get('Problems') or ''
    print('Problem List:', pl)
    disease_causes = load_disease_causes()
    matches = find_problem_matches(pl, disease_causes=disease_causes)
    print('Matches:', matches)

if __name__ == '__main__':
    main()
