import sqlite3
import os

DATABASE_PATH = "research_bot.db"  

def get_db_connection():
    # Make sure DB file exists
    if not os.path.exists(DATABASE_PATH):
        conn = sqlite3.connect(DATABASE_PATH)
        conn.close()
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Rows as dicts
    return conn