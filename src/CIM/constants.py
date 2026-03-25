"""
Insurance type classification based on observed Primary Cvg/Primary Payer values.

This mapping was derived from the actual `Primary Cvg` values in the Hbox dataset
so classifications are based on substring matches found in the file.

Labels returned (normalized):
- 'medicare advantage'
- 'medicare'
- 'medicaid'
- 'commercial'
- 'self pay'
- 'workers comp'
- 'auto'
- 'veterans'
- 'other'
"""

import os
import pandas as pd

INSURANCE_TYPE_MAP = [
    (['medicare advantage', 'med adv', 'med adv', 'medicareadvantage', 'medicare adv', 'medicare plus'], 'medicare advantage'),
    (['medicare part', 'medicare/medicare', 'medicare rail', 'medicare'], 'medicare'),
    (['medicaid', 'health link', 'mi health link', 'healthy mi', 'medicaid hmo'], 'medicaid'),
    (['dual', 'd-snp', 'duals', 'dual complete', 'd-snp', 'snp'], 'medicare advantage'),
    (['advantage', 'med adv', 'med adv ppo', 'med adv hmo', 'med adv ppo'], 'medicare advantage'),
    (['hap', 'blue', 'blue cross', 'blue care', 'bcn', 'aetna', 'cigna', 'humana', 'priority health', 'united', 'molina', 'meridian', 'wellcare', 'geha', 'align', 'aco', 'ascension', 'trinity', 'mcclaren', 'gravie', 'meritain', 'umr', 'pa i', 'pai', 'cofinity', 'cofinity', 'core', 'core', 'mutual of omaha', 'etna'], 'commercial'),
    (['self pay', 'self-pay', 'selfpay'], 'self pay'),
    (['workers compensation', 'wc ', 'wc '], 'workers comp'),
    (['motor vehicle', 'auto '], 'auto'),
    (['veterans', 'va', 'triwest', 'veterans administration', 'optum va'], 'veterans'),
    (['tricare'], 'government'),
]


def classify_insurance(ins_text: str) -> str:
    if not ins_text or not str(ins_text).strip():
        return ''
    s = str(ins_text).lower()
    for patterns, label in INSURANCE_TYPE_MAP:
        for p in patterns:
            if p and p in s:
                return label
    return 'other'


# Problem-list token -> (cause, icd) mapping will be loaded from src/CIM/mappings/problem_list_mapping.csv
PROBLEM_TO_ICD = {}
_mapping_path = os.path.join(os.path.dirname(__file__), 'src', 'CIM', 'mappings', 'problem_list_mapping.csv')
if os.path.exists(_mapping_path):
    try:
        _df = pd.read_csv(_mapping_path)
        for _, r in _df.iterrows():
            tok = str(r['token']).strip().lower()
            cause = r.get('matched_cause') or ''
            icd = r.get('icd_code') or ''
            PROBLEM_TO_ICD[tok] = {'cause': cause, 'icd': icd}
    except Exception:
        PROBLEM_TO_ICD = {}

# Common synonyms mapping from token substrings to canonical cause name in disease list
SYNONYM_TO_CAUSE = {
    'ashd': 'Coronary Artery Disease',
    'arteriosclerotic heart disease': 'Coronary Artery Disease',
    "pvcs": 'Arrhythmia',
    "pvc": 'Arrhythmia',
    'premature ventricular': 'Arrhythmia',
    'shortness of breath': 'Dyspnea',
    'dyspnea': 'Dyspnea',
    'hypercholesterolemia': 'Hyperlipidemia',
    'hypertension': 'Hypertension',
    'high blood pressure': 'Hypertension'
}
