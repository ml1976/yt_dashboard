#!/usr/bin/env python3
# DESC: Adds a single new channel via URL, extracts ID, fetches category and latest videos.

import sys
import sqlite3
import re
import urllib.request
import subprocess
import json
from db import get_db_connection
from rss_poller import fetch_rss, parse_rss_feed

def add_channel(url):
    print(f"Adding channel: {url}")
    
    # 1. Fetch channel HTML to extract ID and Name
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        
        channel_id = None
        match = re.search(r'<link rel="alternate" type="application/rss\+xml" title="RSS" href="[^\"]+channel_id=(UC[a-zA-Z0-9_-]{22})"', html)
        if match:
            channel_id = match.group(1)
        else:
            match2 = re.search(r'<meta itemprop="channelId" content="(UC[a-zA-Z0-9_-]{22})">', html)
            if match2:
                channel_id = match2.group(1)
                
        if not channel_id:
            return {"error": "Could not extract channel ID from URL. Is it a valid YouTube channel?"}
            
        # Try to extract channel name
        name = "New Channel"
        title_match = re.search(r'<title>(.*?) - YouTube</title>', html)
        if title_match:
            name = title_match.group(1).strip()
            
    except Exception as e:
        return {"error": f"Failed to fetch channel page: {e}"}

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 2. Insert into DB (or ignore if exists)
    try:
        cursor.execute("INSERT INTO channels (name, url, channel_id, local_views) VALUES (?, ?, ?, 0)", 
                       (name, url, channel_id))
        channel_db_id = cursor.lastrowid
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return {"error": "Channel already exists in your dashboard!"}
        
    print(f"Inserted into DB. Fetching category via yt-dlp...")
    
    # 3. Fetch Category immediately via yt-dlp
    category = "Unknown"
    try:
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--dump-json",
            "--playlist-items", "1",
            "--compat-options", "no-youtube-unavailable-videos",
            url
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().split('\n'):
                try:
                    data = json.loads(line)
                    categories = data.get('categories', [])
                    if categories and len(categories) > 0:
                        category = categories[0]
                        cursor.execute("UPDATE channels SET category = ? WHERE id = ?", (category, channel_db_id))
                        conn.commit()
                        break
                except:
                    continue
    except Exception as e:
        print(f"Warning: Category fetch failed: {e}")
        
    print(f"Category set to: {category}. Fetching initial RSS videos...")
        
    # 4. Fetch latest videos via RSS
    feed_root = fetch_rss(channel_id)
    videos_added = 0
    if feed_root is not None:
        videos = parse_rss_feed(feed_root, channel_id)
        for v in videos:
            try:
                cursor.execute('''
                    INSERT OR IGNORE INTO videos (video_id, channel_id, title, published_at, url, thumbnail_url)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (v['video_id'], v['channel_id'], v['title'], v['published_at'], v['url'], v['thumbnail_url']))
                if cursor.rowcount > 0:
                    videos_added += 1
            except:
                pass
        conn.commit()
        
    conn.close()
    return {"success": True, "name": name, "category": category, "videos": videos_added}

if __name__ == "__main__":
    if len(sys.argv) > 1:
        res = add_channel(sys.argv[1])
        print(json.dumps(res))
