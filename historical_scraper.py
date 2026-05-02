#!/usr/bin/env python3
# DESC: Scrapes historical video data for YouTube channels using native Python
# DESC: Extracts channel ID from HTML and uses RSS feeds (fast, no yt-dlp bans)
import sqlite3
import urllib.request
import re
import time
import random
import sys
import subprocess
from datetime import datetime
from db import get_db_connection
from rss_poller import fetch_rss, parse_rss_feed

BATCH_SIZE = 10
DELAY_MIN = 2.0
DELAY_MAX = 4.0

def extract_channel_id(url):
    """Fetches the YouTube channel page and extracts the raw UC... Channel ID."""
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8', errors='ignore')
        
        # Most reliable way: Look for the exact RSS feed URL in the head
        match = re.search(r'<link rel="alternate" type="application/rss\+xml" title="RSS" href="[^\"]+channel_id=(UC[a-zA-Z0-9_-]{22})"', html)
        if match:
            return match.group(1)
            
        # Fallback to meta tag
        match2 = re.search(r'<meta itemprop="channelId" content="(UC[a-zA-Z0-9_-]{22})">', html)
        if match2:
            return match2.group(1)
            
    except Exception as e:
        print(f"Error fetching channel HTML for {url}: {e}")
        
    return None

def update_database(channel_db_id, name, channel_id, videos_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Mark the channel as scraped and save the true channel_id
    try:
        cursor.execute("UPDATE channels SET last_scraped_at = ?, channel_id = ? WHERE id = ?", 
                       (datetime.utcnow().isoformat(), channel_id, channel_db_id))
    except sqlite3.IntegrityError:
        print(f"⚠️ Warning: Channel ID {channel_id} already exists for another channel. Marking as scraped without updating ID.")
        cursor.execute("UPDATE channels SET last_scraped_at = ? WHERE id = ?", 
                       (datetime.utcnow().isoformat(), channel_db_id))
    
    if not videos_data:
        print(f"No videos found for {name}.")
        conn.commit()
        conn.close()
        return

    # Insert videos
    count = 0
    for video in videos_data:
        v_id = video['video_id']
        c_id = video['channel_id']
        title = video['title']
        pub_date = video['published_at']
        v_url = video['url']
        thumb = video['thumbnail_url']
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO videos (video_id, channel_id, title, published_at, url, thumbnail_url)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (v_id, c_id, title, pub_date, v_url, thumb))
            if cursor.rowcount > 0:
                count += 1
        except sqlite3.Error as e:
            print(f"DB Error inserting video {v_id}: {e}")
            
    conn.commit()
    conn.close()
    print(f"Saved {count} new videos for {name}.")

def run_scraper(batch_size=BATCH_SIZE):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Select channels that haven't been scraped yet
    cursor.execute("""
        SELECT id, name, url 
        FROM channels 
        WHERE last_scraped_at IS NULL
        LIMIT ?
    """, (batch_size,))
    channels = cursor.fetchall()
    conn.close()
    
    if not channels:
        print("All channels have been scraped! Initial populating complete.")
        return
        
    print(f"Found {len(channels)} channels to process in this batch (out of total).")
    
    for idx, channel in enumerate(channels):
        channel_db_id, name, url = channel['id'], channel['name'], channel['url']
        print(f"[{idx+1}/{len(channels)}] Fetching history for {name} ({url})...")
        
        channel_id = extract_channel_id(url)
        videos = []
        
        if channel_id:
            # We found the ID, now use the fast RSS feed
            feed_root = fetch_rss(channel_id)
            if feed_root is not None:
                videos = parse_rss_feed(feed_root, channel_id)
        else:
            print(f"⚠️ Could not extract channel ID for {name}")
            
        update_database(channel_db_id, name, channel_id, videos)
            
        # Delay between channels (except the last one)
        if idx < len(channels) - 1:
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            time.sleep(delay)

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else BATCH_SIZE
    run_scraper(limit)
