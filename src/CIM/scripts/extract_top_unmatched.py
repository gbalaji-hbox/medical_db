# No template or output folder references to update in this script
import pandas as pd, re, os
from collections import Counter
SEPARATORS=re.compile(r'[;,|/\\\n]+')
HBOX='src/CIM/Hbox list 3 9 26.xlsx'
MAP='src/CIM/mappings/problem_list_mapping.csv'
out='src/CIM/mappings/problem_list_top_unmatched.csv'
mdf=pd.read_csv(MAP)
unmatched=set(mdf[mdf['matched_cause'].isnull()]['token'].astype(str))

df=pd.read_excel(HBOX, sheet_name='Sheet1', engine='openpyxl')
cnt=Counter()
for s in df['Problem List'].dropna().astype(str):
    tokens=[t.strip() for t in SEPARATORS.split(s) if t.strip()]
    for t in tokens:
        if t in unmatched:
            cnt[t]+=1

top=cnt.most_common(200)
if not os.path.exists('src/CIM/mappings'):
    os.makedirs('src/CIM/mappings')
with open(out,'w',encoding='utf8') as f:
    f.write('token,count\n')
    for t,c in top:
        # escape double quotes
        tt = t.replace('"', '""')
        f.write('"%s",%d\n' % (tt, c))
print('WROTE',out)
