#!/home/mladjo/.virtualenvs/tools/bin/python
# DESC: Background script to fetch generic YouTube Trending videos using yt-dlp.

import sqlite3
import os
import subprocess
import json
from datetime import datetime
from db import get_db_connection

def fetch_trending():
    lock_file = os.path.join(os.path.dirname(__file__), "data", "trending.lock")
    if os.path.exists(lock_file):
        print("Trending fetcher is already running.")
        return
        
    with open(lock_file, "w") as f:
        f.write("running")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Fetching trending videos...")
        
        cmd = [
            "/usr/bin/yt-dlp",
            "--dump-json",
            "--flat-playlist",
            "ytsearch15:trending viral popular today"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.stdout:
            cursor.execute("DELETE FROM videos WHERE channel_id = 'VIRTUAL_TRENDING'")
            
            count = 0
            for line in result.stdout.strip().split('\n'):
                try:
                    data = json.loads(line)
                    v_id = data.get('id')
                    title = data.get('title', 'Unknown')
                    channel_name = data.get('uploader', 'Unknown Channel')
                    v_url = f"https://www.youtube.com/watch?v={v_id}"
                    
                    display_title = f"[{channel_name}] {title}"
                    
                    thumbs = data.get('thumbnails', [])
                    thumbnail_url = thumbs[-1].get('url', '') if thumbs else ""
                    pub_date = datetime.utcnow().isoformat()
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO videos (video_id, channel_id, title, published_at, url, thumbnail_url)
                        VALUES (?, 'VIRTUAL_TRENDING', ?, ?, ?, ?)
                    ''', (v_id, display_title, pub_date, v_url, thumbnail_url))
                    
                    count += 1
                except Exception as e:
                    continue
                    
            conn.commit()
            print(f"Added {count} trending videos to VIRTUAL_TRENDING.")
            
    finally:
        conn.close()
        if os.path.exists(lock_file):
            os.remove(lock_file)

if __name__ == "__main__":
    fetch_trending()
