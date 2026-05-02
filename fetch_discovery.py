import sys
#!/usr/bin/env python3
# DESC: Background script to fetch "New to You" discovery videos using yt-dlp.

import sqlite3
import os
import subprocess
import json
import random
from datetime import datetime
from db import get_db_connection

def fetch_discovery():
    lock_file = os.path.join(os.path.dirname(__file__), "data", "discovery.lock")
    if os.path.exists(lock_file):
        print("Discovery fetcher is already running.")
        return
        
    with open(lock_file, "w") as f:
        f.write("running")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Find top watched channels
        cursor.execute("""
            SELECT c.channel_id, c.name 
            FROM channels c 
            WHERE c.local_views > 0 AND c.channel_id NOT LIKE 'VIRTUAL_%' 
            ORDER BY c.local_views DESC 
            LIMIT 5
        """)
        top_channels = cursor.fetchall()
        
        if not top_channels:
            print("Not enough watch history for discovery.")
            return
            
        # 2. Pick a random top channel to base the search on
        target_channel = random.choice(top_channels)
        print(f"Basing discovery on favorite channel: {target_channel['name']}")
        
        # 3. Get recent video title from that channel
        cursor.execute("""
            SELECT title FROM videos 
            WHERE channel_id = ? 
            ORDER BY published_at DESC LIMIT 5
        """, (target_channel['channel_id'],))
        recent_videos = cursor.fetchall()
        
        if not recent_videos:
            print("No recent videos found for the target channel.")
            return
            
        target_video = random.choice(recent_videos)['title']
        
        # We clean up the title to make a broader search query (take first half of title)
        search_query = target_video.split('|')[0].split('-')[0].strip()
        print(f"Search Query for Discovery: {search_query}")
        
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--dump-json",
            "--flat-playlist",
            f"ytsearch15:{search_query}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.stdout:
            cursor.execute("DELETE FROM videos WHERE channel_id = 'VIRTUAL_DISCOVERY'")
            
            # Load all existing subscribed channel IDs for filtering
            cursor.execute("SELECT channel_id FROM channels WHERE channel_id NOT LIKE 'VIRTUAL_%'")
            subscribed_ids = {row['channel_id'] for row in cursor.fetchall()}
            
            count = 0
            for line in result.stdout.strip().split('\n'):
                try:
                    data = json.loads(line)
                    v_id = data.get('id')
                    c_id = data.get('channel_id')
                    title = data.get('title', 'Unknown')
                    channel_name = data.get('uploader', 'Unknown Channel')
                    v_url = f"https://www.youtube.com/watch?v={v_id}"
                    
                    # If this is from a channel we already subscribe to, SKIP it!
                    if c_id in subscribed_ids:
                        continue
                        
                    # Prepend channel name so the user knows who it's from in the virtual row
                    display_title = f"[{channel_name}] {title}"
                    
                    thumbs = data.get('thumbnails', [])
                    thumbnail_url = thumbs[-1].get('url', '') if thumbs else ""
                    pub_date = datetime.utcnow().isoformat()
                    
                    cursor.execute('''
                        INSERT OR IGNORE INTO videos (video_id, channel_id, title, published_at, url, thumbnail_url)
                        VALUES (?, 'VIRTUAL_DISCOVERY', ?, ?, ?, ?)
                    ''', (v_id, display_title, pub_date, v_url, thumbnail_url))
                    
                    count += 1
                except Exception as e:
                    continue
                    
            conn.commit()
            print(f"Added {count} New to You videos to VIRTUAL_DISCOVERY.")
            
    finally:
        conn.close()
        if os.path.exists(lock_file):
            os.remove(lock_file)

if __name__ == "__main__":
    fetch_discovery()
