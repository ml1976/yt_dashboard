#!/usr/bin/env python3
# DESC: Database schema and connection management for YT Dashboard
# DESC: Initializes the SQLite database for channels and videos

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "yt_dashboard.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create channels table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS channels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        url TEXT UNIQUE NOT NULL,
        channel_id TEXT UNIQUE,
        last_scraped_at DATETIME,
        local_views INTEGER DEFAULT 0,
        category TEXT
    )
    ''')
    
    # Check if columns exist for backward compatibility
    cursor.execute("PRAGMA table_info(channels)")
    columns = [col['name'] for col in cursor.fetchall()]
    if 'last_scraped_at' not in columns:
        cursor.execute("ALTER TABLE channels ADD COLUMN last_scraped_at DATETIME")
    if 'local_views' not in columns:
        cursor.execute("ALTER TABLE channels ADD COLUMN local_views INTEGER DEFAULT 0")
    if 'category' not in columns:
        cursor.execute("ALTER TABLE channels ADD COLUMN category TEXT")
    if 'custom_folder' not in columns:
        cursor.execute("ALTER TABLE channels ADD COLUMN custom_folder TEXT")
        
    # Create videos table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS videos (
        video_id TEXT PRIMARY KEY,
        channel_id TEXT NOT NULL,
        title TEXT NOT NULL,
        published_at DATETIME NOT NULL,
        url TEXT NOT NULL,
        thumbnail_url TEXT,
        is_favorite BOOLEAN DEFAULT 0,
        watch_progress REAL DEFAULT 0.0,
        is_watched BOOLEAN DEFAULT 0,
        FOREIGN KEY(channel_id) REFERENCES channels(channel_id)
    )
    ''')
    
    # Check if columns exist for backward compatibility on videos
    cursor.execute("PRAGMA table_info(videos)")
    v_columns = [col['name'] for col in cursor.fetchall()]
    if 'is_favorite' not in v_columns:
        cursor.execute("ALTER TABLE videos ADD COLUMN is_favorite BOOLEAN DEFAULT 0")
    if 'watch_progress' not in v_columns:
        cursor.execute("ALTER TABLE videos ADD COLUMN watch_progress REAL DEFAULT 0.0")
    if 'is_watched' not in v_columns:
        cursor.execute("ALTER TABLE videos ADD COLUMN is_watched BOOLEAN DEFAULT 0")
    if 'is_watch_later' not in v_columns:
        cursor.execute("ALTER TABLE videos ADD COLUMN is_watch_later BOOLEAN DEFAULT 0")
        
    # Create settings table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    ''')
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")

if __name__ == "__main__":
    init_db()
