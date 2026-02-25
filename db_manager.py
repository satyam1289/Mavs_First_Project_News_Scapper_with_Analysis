import sqlite3
import json
import os
from datetime import datetime

DB_NAME = "articles.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Articles Table
    # We use 'link' as the Primary Key to prevent duplicates automatically
    c.execute('''
        CREATE TABLE IF NOT EXISTS articles (
            link TEXT PRIMARY KEY,
            title TEXT,
            source TEXT,
            published TEXT,
            summary TEXT,
            full_text TEXT,
            sector TEXT,
            derived_topics TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Validation Table (for scraping stats)
    c.execute('''
        CREATE TABLE IF NOT EXISTS scraping_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain TEXT,
            status TEXT,
            error_message TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Analysis Cache Table
    # Stores results of analyze_specific_brands to speed up repeated queries
    c.execute('''
        CREATE TABLE IF NOT EXISTS analysis_cache (
            brand_id TEXT PRIMARY KEY, 
            analysis_data TEXT,
            article_count_at_analysis INTEGER,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_articles(articles_list):
    """
    Bulk upsert articles into the database.
    Ignores duplicates based on 'link'.
    """
    if not articles_list:
        return 0
        
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    count = 0
    for a in articles_list:
        try:
            # Prepare data
            link = a.get('link')
            if not link: continue
            
            title = a.get('title', '')
            source = a.get('source', '')
            published = str(a.get('published', ''))
            summary = a.get('summary', '')
            full_text = a.get('full_text', '')
            sector = a.get('sector', '')
            
            # Convert list topics to string if needed
            topics = a.get('derived_topics', [])
            if isinstance(topics, list):
                topics = json.dumps(topics)
            
            c.execute('''
                INSERT OR IGNORE INTO articles 
                (link, title, source, published, summary, full_text, sector, derived_topics)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (link, title, source, published, summary, full_text, sector, topics))
            
            if c.rowcount > 0:
                count += 1
                
        except Exception as e:
            print(f"DB Error saving article {link}: {e}")
            
    conn.commit()
    conn.close()
    return count

def get_articles(limit=50, offset=0, sector_filter=None, search_query=None):
    """
    Fetch articles with pagination and filtering.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # To access columns by name
    c = conn.cursor()
    
    query = "SELECT * FROM articles WHERE 1=1"
    params = []
    
    if sector_filter and sector_filter != "All":
        query += " AND sector = ?"
        params.append(sector_filter)
        
    if search_query:
        # Simple LIKE search
        query += " AND (title LIKE ? OR full_text LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard])
        
    query += " ORDER BY published ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    # Convert Row objects to dicts
    return [dict(row) for row in rows]

def get_total_count(sector_filter=None, search_query=None):
    """
    Get total count for pagination.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    query = "SELECT COUNT(*) FROM articles WHERE 1=1"
    params = []
    
    if sector_filter and sector_filter != "All":
        query += " AND sector = ?"
        params.append(sector_filter)
        
    if search_query:
        query += " AND (title LIKE ? OR full_text LIKE ?)"
        wildcard = f"%{search_query}%"
        params.extend([wildcard, wildcard])
        
    c.execute(query, params)
    count = c.fetchone()[0]
    conn.close()
    return count

def get_db_sql_dump():
    """
    Returns a full SQL dump of the entire database.
    """
    conn = sqlite3.connect(DB_NAME)
    dump_lines = list(conn.iterdump())
    conn.close()
    return "\n".join(dump_lines)

def get_stats():
    """
    Get simple stats for dashboard.
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM articles")
    total = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT source) FROM articles")
    sources = c.fetchone()[0]
    
    conn.close()
    return {"total_articles": total, "total_sources": sources}

def get_cached_analysis(brand_name):
    """Retrieve cached analysis if it exists."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT analysis_data, article_count_at_analysis FROM analysis_cache WHERE brand_id = ?", (brand_name.lower().strip(),))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0]), row[1]
    return None, 0

def save_analysis_cache(brand_name, analysis_data, current_article_count):
    """Save analysis results to cache."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    brand_id = brand_name.lower().strip()
    data_str = json.dumps(analysis_data)
    c.execute('''
        INSERT OR REPLACE INTO analysis_cache (brand_id, analysis_data, article_count_at_analysis, last_updated)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
    ''', (brand_id, data_str, current_article_count))
    conn.commit()
    conn.close()

# Init on load
init_db()

