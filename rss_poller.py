#!/home/mladjo/.virtualenvs/tools/bin/python
# DESC: Fetches YouTube channel metadata via RSS without using an API Key.
# DESC: Parses XML feed into a structured format for local storage.
# DESC: Designed to run as a cron job to keep the YT Dashboard updated.

import urllib.request
import xml.etree.ElementTree as ET
import sqlite3
import os
from db import get_db_connection

def fetch_rss(channel_id):
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            return ET.fromstring(xml_data)
    except Exception as e:
        print(f"ERROR: Failed to fetch RSS for {channel_id}: {e}")
        return None

def parse_rss_feed(root, channel_id):
    ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015', 'media': 'http://search.yahoo.com/mrss/'}
    
    videos = []
    
    for entry in root.findall('atom:entry', ns):
        video_id = entry.find('yt:videoId', ns).text
        title = entry.find('atom:title', ns).text
        published = entry.find('atom:published', ns).text
        
        # Try to get thumbnail from media:group
        thumbnail_url = ""
        media_group = entry.find('media:group', ns)
        if media_group is not None:
            media_thumb = media_group.find('media:thumbnail', ns)
            if media_thumb is not None:
                thumbnail_url = media_thumb.attrib.get('url', '')
                
        videos.append({
            "video_id": video_id,
            "channel_id": channel_id,
            "title": title,
            "published_at": published,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "thumbnail_url": thumbnail_url
        })
    return videos

def run_rss_poller():
    lock_file = os.path.join(os.path.dirname(__file__), "data", "rss.lock")
    if os.path.exists(lock_file):
        print("RSS Poller is already running.")
        return
        
    with open(lock_file, "w") as f:
        f.write("running")
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # We can only use RSS feeds for channels where we know the channel_id
        # Prioritize most watched channels, then least recently scraped
        cursor.execute("SELECT name, channel_id FROM channels WHERE channel_id IS NOT NULL ORDER BY local_views DESC, last_scraped_at ASC")
        channels = cursor.fetchall()
        
        total_added = 0
        
        print(f"Polling RSS for {len(channels)} channels...")
        
        for channel in channels:
            name, channel_id = channel['name'], channel['channel_id']
            
            feed_root = fetch_rss(channel_id)
            if feed_root is not None:
                videos = parse_rss_feed(feed_root, channel_id)
                
                added_for_channel = 0
                for v in videos:
                    try:
                        cursor.execute('''
                            INSERT OR IGNORE INTO videos (video_id, channel_id, title, published_at, url, thumbnail_url)
                            VALUES (?, ?, ?, ?, ?, ?)
                        ''', (v['video_id'], v['channel_id'], v['title'], v['published_at'], v['url'], v['thumbnail_url']))
                        
                        if cursor.rowcount > 0:
                            added_for_channel += 1
                            total_added += 1
                    except sqlite3.Error as e:
                        print(f"DB Error inserting {v['video_id']}: {e}")
                        
                if added_for_channel > 0:
                    print(f"Added {added_for_channel} new videos for {name}")
                    
        conn.commit()
        conn.close()
        print(f"RSS Polling complete. Total new videos added: {total_added}")
    finally:
        if os.path.exists(lock_file):
            os.remove(lock_file)

if __name__ == "__main__":
    run_rss_poller()
