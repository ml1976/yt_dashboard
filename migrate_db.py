#!/home/mladjo/.virtualenvs/tools/bin/python
import sqlite3
import os
from db import get_db_connection

def migrate():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Helper to check if a column exists
    def column_exists(table, col_name):
        cursor.execute(f"PRAGMA table_info({table})")
        cols = [col['name'] for col in cursor.fetchall()]
        return col_name in cols

    print("Running database migrations without deleting data...")
    
    # Update channels table
    if not column_exists('channels', 'local_views'):
        print("Adding local_views to channels...")
        cursor.execute("ALTER TABLE channels ADD COLUMN local_views INTEGER DEFAULT 0")
        
    if not column_exists('channels', 'category'):
        print("Adding category to channels...")
        cursor.execute("ALTER TABLE channels ADD COLUMN category TEXT")
        
    # Update videos table
    if not column_exists('videos', 'is_favorite'):
        print("Adding is_favorite to videos...")
        cursor.execute("ALTER TABLE videos ADD COLUMN is_favorite BOOLEAN DEFAULT 0")
        
    if not column_exists('videos', 'watch_progress'):
        print("Adding watch_progress to videos...")
        cursor.execute("ALTER TABLE videos ADD COLUMN watch_progress REAL DEFAULT 0.0")
        
    if not column_exists('videos', 'is_watched'):
        print("Adding is_watched to videos...")
        cursor.execute("ALTER TABLE videos ADD COLUMN is_watched BOOLEAN DEFAULT 0")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    migrate()
