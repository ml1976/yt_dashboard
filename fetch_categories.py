#!/home/mladjo/.virtualenvs/tools/bin/python
# DESC: Background script to fetch channel categories (genres) using yt-dlp.
# DESC: Designed to run slowly to avoid bans.

import sqlite3
import os
import subprocess
import json
import time
import random
from db import get_db_connection

def fetch_categories():
    lock_file = os.path.join(os.path.dirname(__file__), "data", "categories.lock")
    if os.path.exists(lock_file):
        print("Category fetcher is already running.")
        return
        
    with open(lock_file, "w") as f:
        f.write("running")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get channels that don't have a category yet
        cursor.execute("SELECT id, name, url FROM channels WHERE category IS NULL")
        channels = cursor.fetchall()
        
        print(f"Fetching categories for {len(channels)} channels...")
        
        for ch in channels:
            name, url, ch_id = ch['name'], ch['url'], ch['id']
            print(f"Fetching category for {name}...")
            
            try:
                # We only need info from 1 video to get the channel's general category
                cmd = [
                    "/usr/bin/yt-dlp",
                    "--dump-json",
                    "--playlist-items", "1",
                    "--compat-options", "no-youtube-unavailable-videos",
                    url
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and result.stdout:
                    # It might return multiple lines if it's a playlist, just parse the first valid JSON
                    for line in result.stdout.strip().split('\n'):
                        try:
                            data = json.loads(line)
                            categories = data.get('categories', [])
                            if categories and len(categories) > 0:
                                category = categories[0]
                                cursor.execute("UPDATE channels SET category = ? WHERE id = ?", (category, ch_id))
                                conn.commit()
                                print(f" -> Found category: {category}")
                                break # Found it, go to next channel
                        except json.JSONDecodeError:
                            continue
                else:
                    print(f" -> No category found (yt-dlp failed or returned no data)")
                    
            except subprocess.TimeoutExpired:
                print(f" -> Timeout fetching {name}")
            except Exception as e:
                print(f" -> Error: {e}")
                
            # Random delay to prevent rate-limiting (2 to 5 seconds)
            delay = random.uniform(2.0, 5.0)
            time.sleep(delay)
            
        print("Category fetching complete.")
    finally:
        if os.path.exists(lock_file):
            os.remove(lock_file)

if __name__ == "__main__":
    fetch_categories()
