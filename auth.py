import sqlite3
import os

DB_NAME = "users.db"

def init_db():
    """Initializes the database and creates the users table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def create_user(username, password):
    """Creates a new user with a plain text password (INSECURE). Returns True if successful, False if username exists."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Check if user already exists
    c.execute('SELECT username FROM users WHERE username = ?', (username,))
    if c.fetchone():
        conn.close()
        return False
    
    # WARNING: Storing password in plain text as per user request
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
        
    conn.close()
    return success

def check_credentials(username, password):
    """Verifies a user's password. Returns True if correct, False otherwise."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    
    if result:
        stored_password = result[0]
        # Direct comparison for plain text
        if password == stored_password:
            return True
            
    return False

def authenticate_user(username, password):
    """
    Verifies a user's password with detailed feedback.
    Returns: (success: bool, message: str)
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    c.execute('SELECT password FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    conn.close()
    
    if not result:
        return False, "User not found"
        
    stored_password = result[0]
    # Direct comparison for plain text
    if password == stored_password:
        return True, "Login successful"
    else:
        return False, "Incorrect password"

# Initialize the database when this module is imported (or called explicitly)
if not os.path.exists(DB_NAME):
    init_db()
