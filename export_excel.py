import sqlite3
import pandas as pd
from dateutil import parser

conn = sqlite3.connect('articles.db')
df = pd.read_sql_query("SELECT * FROM articles", conn)

def is_in_range(date_str):
    if not date_str:
        return False
    try:
        dt = parser.parse(date_str)
        return dt.month == 2 and 1 <= dt.day <= 7
    except Exception as e:
        return False

filtered_df = df[df['published'].apply(is_in_range)]
output_filename = 'articles_feb_01_to_07.xlsx'
filtered_df.to_excel(output_filename, index=False)
print(f"Successfully exported {len(filtered_df)} articles to {output_filename}.")
