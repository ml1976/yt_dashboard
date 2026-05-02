#!/home/mladjo/.virtualenvs/tools/bin/python
# DESC: Background script to fetch popular live streams using yt-dlp.

import sqlite3
import os
import subprocess
import json
import time
from datetime import datetime
from db import get_db_connection

def fetch_live_streams():
    lock_file = os.path.join(os.path.dirname(__file__), "data", "live.lock")
    if os.path.exists(lock_file):
        print("Live fetcher is already running.")
        return
        
    with open(lock_file, "w") as f:
        f.write("running")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("Fetching top live streams...")
        
        cmd = [
            "/usr/bin/yt-dlp",
            "--dump-json",
            "--flat-playlist",
            "ytsearch50:live"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        # yt-dlp might return a non-zero exit code if some videos fail to parse,
        # but it will still output valid JSON for the successful ones in stdout.
        if result.stdout:
            # Clear old live streams first so it's always fresh
            cursor.execute("DELETE FROM videos WHERE channel_id = 'VIRTUAL_LIVE'")
            
            count = 0
            for line in result.stdout.strip().split('\n'):
                try:
                    data = json.loads(line)
                    v_id = data.get('id')
                    title = data.get('title', 'Unknown Live Stream')
                    v_url = f"https://www.youtube.com/watch?v={v_id}"
                    channel_name = data.get('channel', data.get('uploader', ''))
                    
                    # Try to get best thumbnail
                    thumbs = data.get('thumbnails', [])
                    thumbnail_url = ""
                    if thumbs:
                        thumbnail_url = thumbs[-1].get('url', '')
                        
                    pub_date = datetime.utcnow().isoformat() # Live now
                    
                    # Check if this live stream is from one of our subscribed channels
                    cursor.execute("SELECT 1 FROM channels WHERE name = ?", (channel_name,))
                    is_subscribed = 1 if cursor.fetchone() else 0
                    
                    if is_subscribed:
                        title = f"[★ FROM SUBSCRIPTION] {title}"
                    
                    # Prepend LIVE_ to avoid primary key collisions if the video is already 
                    # in the database under its real channel from an RSS scrape
                    live_video_id = f"LIVE_{v_id}"
                    
                    # Ensure we only insert actual live streams
                    if data.get('live_status') != 'is_live':
                        continue # Skip it, it's not actually live right now
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO videos (video_id, channel_id, title, published_at, url, thumbnail_url, is_favorite)
                        VALUES (?, 'VIRTUAL_LIVE', ?, ?, ?, ?, ?)
                    ''', (live_video_id, title, pub_date, v_url, thumbnail_url, is_subscribed))
                    
                    count += 1
                except Exception as e:
                    print(f"Error parsing live stream JSON: {e}")
                    continue
                    
            conn.commit()
            print(f"Added {count} live streams to VIRTUAL_LIVE.")
        else:
            print(f"yt-dlp failed to fetch live streams: {result.stderr}")
            
    finally:
        conn.close()
        if os.path.exists(lock_file):
            os.remove(lock_file)

if __name__ == "__main__":
    fetch_live_streams()
