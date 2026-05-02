#!/home/mladjo/.virtualenvs/tools/bin/python
# DESC: Scrapes older historical video data for a specific channel
import sqlite3
import subprocess
import json
import sys
from db import get_db_connection

def load_older_videos(channel_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT name, url FROM channels WHERE channel_id = ?", (channel_id,))
    channel = cursor.fetchone()
    if not channel:
        print(f"Error: Channel {channel_id} not found in DB.")
        return
        
    name, url = channel['name'], channel['url']
    print(f"Loading older videos for {name} ({url})...")
    
    videos_data = []
    
    # Try /videos first, then /streams
    for tab in ['/videos', '/streams']:
        cmd = [
            "/usr/bin/yt-dlp",
            "--dump-json",
            "--playlist-items", "1-50",
            "--ignore-errors",
            f"{url.rstrip('/')}{tab}"
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            
            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                try:
                    video = json.loads(line)
                    if not any(v.get('id') == video.get('id') for v in videos_data):
                        videos_data.append(video)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            print(f"Error executing yt-dlp for {name} on {tab}: {e}")
            
    if not videos_data:
        print(f"No videos found for {name}.")
        conn.close()
        return

    # Insert videos
    count = 0
    for video in videos_data:
        v_id = video.get('id')
        c_id = video.get('channel_id') or channel_id
        title = video.get('title')
        
        upload_date = video.get('upload_date')
        if upload_date and len(upload_date) == 8:
            pub_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}T00:00:00Z"
        else:
            pub_date = "1970-01-01T00:00:00Z"
            
        v_url = video.get('webpage_url') or f"https://www.youtube.com/watch?v={v_id}"
        thumb = video.get('thumbnail')
        
        if not v_id or not title:
            continue
            
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO videos (video_id, channel_id, title, published_at, url, thumbnail_url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (v_id, c_id, title, pub_date, v_url, thumb))
            if cursor.rowcount > 0:
                count += 1
        except sqlite3.Error as e:
            pass
            
    conn.commit()
    conn.close()
    print(f"Saved {count} older videos for {name}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python load_older.py <channel_id>")
        sys.exit(1)
    
    channel_id = sys.argv[1]
    load_older_videos(channel_id)
