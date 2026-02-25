import pandas as pd
import json

df = pd.read_excel('jan_complete.xlsx')
data = df.head(5).to_dict(orient='records')
columns = df.columns.tolist()

with open('inspect_out.json', 'w') as f:
    json.dump({'columns': columns, 'sample': data}, f, indent=2)

print("done")
