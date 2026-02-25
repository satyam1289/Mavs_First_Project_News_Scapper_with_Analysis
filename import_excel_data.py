import pandas as pd
import sqlite3
from db_manager import save_articles

def import_excel_to_db():
    print("Loading Excel file...")
    df = pd.read_excel('jan_complete.xlsx')
    
    print(f"Initial row count: {len(df)}")
    
    # Drop duplicates
    df = df.drop_duplicates(subset=['link'], keep='first')
    print(f"Row count after dropping duplicates: {len(df)}")
    
    # Parse dates and sort by ascending order
    # Convert 'published' to datetime to sort correctly
    df['published_dt'] = pd.to_datetime(df['published'], errors='coerce')
    df = df.sort_values(by='published_dt', ascending=True)
    df = df.drop(columns=['published_dt'])
    
    # Fill NaN values with empty strings
    df = df.fillna('')
    
    # Convert to list of dicts
    articles = df.to_dict(orient='records')
    
    # Save to db
    print("Saving to database...")
    count = save_articles(articles)
    
    print(f"Successfully added {count} new articles to the database.")

if __name__ == "__main__":
    import_excel_to_db()
