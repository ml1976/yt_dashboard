#!/home/mladjo/.virtualenvs/tools/bin/python
# DESC: Parses Google Takeout watch-history.json to populate local_views and is_watched status
import json
import sqlite3
import os
import re
from db import get_db_connection

def import_history():
    history_path = os.path.join(os.path.dirname(__file__), "data", "watch-history.json")
    if not os.path.exists(history_path):
        print(f"File not found: {history_path}")
        return

    print("Loading watch history JSON...")
    with open(history_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    conn = get_db_connection()
    cursor = conn.cursor()

    video_views = set() # Store watched video IDs
    channel_views = {}  # Store view counts for channels

    for entry in data:
        if entry.get("header") != "YouTube":
            continue

        # Extract video ID
        title_url = entry.get("titleUrl", "")
        match = re.search(r'v=([a-zA-Z0-9_-]+)', title_url)
        if match:
            video_views.add(match.group(1))

        # Extract channel ID
        subtitles = entry.get("subtitles", [])
        if subtitles:
            channel_url = subtitles[0].get("url", "")
            match = re.search(r'channel/(UC[a-zA-Z0-9_-]{22})', channel_url)
            if match:
                channel_id = match.group(1)
                channel_views[channel_id] = channel_views.get(channel_id, 0) + 1

    print(f"Found {len(video_views)} unique watched videos and {len(channel_views)} unique channels in history.")

    # Update watched videos (batch)
    print("Updating watched videos in database...")
    cursor.executemany(
        "UPDATE videos SET is_watched = 1 WHERE video_id = ?",
        [(vid,) for vid in video_views]
    )

    # Update channel views (batch)
    print("Updating channel views in database...")
    # Add to existing views (if any) instead of overwriting, though it should be zero mostly.
    cursor.executemany(
        "UPDATE channels SET local_views = local_views + ? WHERE channel_id = ?",
        [(count, cid) for cid, count in channel_views.items()]
    )

    conn.commit()
    
    # Let's print out the top 5 updated channels to verify
    cursor.execute("SELECT name, local_views FROM channels ORDER BY local_views DESC LIMIT 5")
    top_channels = cursor.fetchall()
    print("\nTop 5 Most Watched Channels after import:")
    for ch in top_channels:
        print(f" - {ch['name']}: {ch['local_views']} views")
        
    conn.close()
    print("\nImport complete!")

if __name__ == "__main__":
    import_history()