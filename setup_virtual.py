#!/usr/bin/env python3
import sqlite3
import os
from db import get_db_connection

def setup_virtual_channels():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert Virtual Live channel
    try:
        cursor.execute("INSERT INTO channels (name, url, channel_id, local_views, category) VALUES (?, ?, ?, ?, ?)",
                       ("Top Live Streams (Current global live broadcasts)", "https://www.youtube.com/live", "VIRTUAL_LIVE", 999999, "Live"))
    except sqlite3.IntegrityError:
        pass # Already exists
        
    # Insert Virtual Home channel
    try:
        cursor.execute("INSERT INTO channels (name, url, channel_id, local_views, category) VALUES (?, ?, ?, ?, ?)",
                       ("Recommended For You (Unwatched videos from your favorite subscriptions)", "http://localhost:8080", "VIRTUAL_HOME", 1000000, "Home"))
    except sqlite3.IntegrityError:
        pass # Already exists
        
    # Insert Virtual Discovery channel
    try:
        cursor.execute("INSERT INTO channels (name, url, channel_id, local_views, category) VALUES (?, ?, ?, ?, ?)",
                       ("New to You (Discovery) (New channels discussing topics you love)", "http://localhost:8080/discovery", "VIRTUAL_DISCOVERY", 999998, "Discovery"))
    except sqlite3.IntegrityError:
        pass # Already exists
        
    # Insert Virtual Trending channel
    try:
        cursor.execute("INSERT INTO channels (name, url, channel_id, local_views, category) VALUES (?, ?, ?, ?, ?)",
                       ("YouTube Trending (Generic viral videos)", "https://www.youtube.com/feed/trending", "VIRTUAL_TRENDING", 999997, "Trending"))
    except sqlite3.IntegrityError:
        pass # Already exists
        
    # Insert Virtual Watch Later
    try:
        cursor.execute("INSERT INTO channels (name, url, channel_id, local_views, category) VALUES (?, ?, ?, ?, ?)",
                       ("Watch Later Queue (Your locally saved queue)", "http://localhost:8080/watch_later", "VIRTUAL_WATCH_LATER", 1000002, "Queue"))
    except sqlite3.IntegrityError:
        pass # Already exists

    # Insert Virtual Favorites
    try:
        cursor.execute("INSERT INTO channels (name, url, channel_id, local_views, category) VALUES (?, ?, ?, ?, ?)",
                       ("My Favorites (Videos you have starred)", "http://localhost:8080/favorites", "VIRTUAL_FAVORITES", 1000001, "Queue"))
    except sqlite3.IntegrityError:
        pass # Already exists
        
    conn.commit()
    conn.close()
    print("Virtual channels setup complete.")

if __name__ == "__main__":
    setup_virtual_channels()