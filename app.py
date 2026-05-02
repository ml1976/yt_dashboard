#!/home/mladjo/.virtualenvs/tools/bin/python
# DESC: A lightweight web server using ONLY the standard library
# DESC: Serves the YT Dashboard frontend and provides an API for video data

import json
import sqlite3
import os
from http.server import SimpleHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from db import get_db_connection

PORT = 8080
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Ensure directories exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

class YTDashboardHandler(SimpleHTTPRequestHandler):
    
    def do_GET(self):
        parsed_url = urlparse(self.path)
        
        # API Endpoint: Get status of background tasks
        if parsed_url.path == '/api/status':
            rss_running = os.path.exists(os.path.join(os.path.dirname(__file__), "data", "rss.lock"))
            categories_running = os.path.exists(os.path.join(os.path.dirname(__file__), "data", "categories.lock"))
            live_running = os.path.exists(os.path.join(os.path.dirname(__file__), "data", "live.lock"))
            discovery_running = os.path.exists(os.path.join(os.path.dirname(__file__), "data", "discovery.lock"))
            trending_running = os.path.exists(os.path.join(os.path.dirname(__file__), "data", "trending.lock"))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "rss_running": rss_running, 
                "categories_running": categories_running,
                "live_running": live_running,
                "discovery_running": discovery_running,
                "trending_running": trending_running
            }).encode('utf-8'))
            return

        # API Endpoint: Get the structured EPG timeline data
        if parsed_url.path == '/api/timeline':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            data = self.get_timeline_data()
            self.wfile.write(json.dumps(data).encode('utf-8'))
            return
            
        # API Endpoint: Get settings
        if parsed_url.path == '/api/settings':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM settings")
            settings = {row['key']: json.loads(row['value']) if row['value'].startswith('[') else row['value'] for row in cursor.fetchall()}
            conn.close()
            
            self.wfile.write(json.dumps(settings).encode('utf-8'))
            return
            
        # Root Endpoint: Serve index.html
        if parsed_url.path == '/' or parsed_url.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            with open(os.path.join(TEMPLATES_DIR, 'index.html'), 'rb') as f:
                self.wfile.write(f.read())
            return
            
        # Serve static files (CSS/JS)
        if parsed_url.path.startswith('/static/'):
            filepath = os.path.join(os.path.dirname(__file__), parsed_url.path.lstrip('/'))
            if os.path.exists(filepath):
                self.send_response(200)
                if filepath.endswith('.css'):
                    self.send_header('Content-type', 'text/css')
                elif filepath.endswith('.js'):
                    self.send_header('Content-type', 'application/javascript')
                self.end_headers()
                
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
                return
                
        # 404 for anything else
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def do_POST(self):
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/api/settings':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            conn = get_db_connection()
            cursor = conn.cursor()
            for key, value in data.items():
                val_str = json.dumps(value) if isinstance(value, list) else str(value)
                cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val_str))
            conn.commit()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            return
            
        if parsed_url.path == '/api/set_custom_folder':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            channel_id = data.get('channel_id')
            custom_folder = data.get('custom_folder', '')
            
            if channel_id:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE channels SET custom_folder = ? WHERE channel_id = ?", (custom_folder, channel_id))
                conn.commit()
                conn.close()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()
            return

        if parsed_url.path == '/api/track_click':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            channel_id = data.get('channel_id')
            video_id = data.get('video_id')
            
            if channel_id and video_id:
                live_video_id = f"LIVE_{video_id}"
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE channels SET local_views = local_views + 1 WHERE channel_id = ?", (channel_id,))
                cursor.execute("UPDATE videos SET is_watched = 1 WHERE video_id = ? OR video_id = ?", (video_id, live_video_id))
                conn.commit()
                conn.close()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()
            return

        if parsed_url.path == '/api/toggle_favorite':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            video_id = data.get('video_id')
            is_favorite = data.get('is_favorite')
            
            if video_id is not None and is_favorite is not None:
                live_video_id = f"LIVE_{video_id}"
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE videos SET is_favorite = ? WHERE video_id = ? OR video_id = ?", (int(is_favorite), video_id, live_video_id))
                conn.commit()
                conn.close()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()
            return
            
        if parsed_url.path == '/api/toggle_watch_later':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            video_id = data.get('video_id')
            is_watch_later = data.get('is_watch_later')
            
            if video_id is not None and is_watch_later is not None:
                live_video_id = f"LIVE_{video_id}"
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE videos SET is_watch_later = ? WHERE video_id = ? OR video_id = ?", (int(is_watch_later), video_id, live_video_id))
                conn.commit()
                conn.close()
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()
            return
            
        if parsed_url.path == '/api/scrape_rss':
            # Run the RSS poller in the background so we don't block the UI
            os.system(f"/home/mladjo/.virtualenvs/tools/bin/python {os.path.join(os.path.dirname(__file__), 'rss_poller.py')} &")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "RSS polling started in background. The UI will automatically update when finished."}).encode('utf-8'))
            return
            
        if parsed_url.path == '/api/add_channel':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            url = data.get('url')
            
            if url:
                import subprocess
                cmd = ["/home/mladjo/.virtualenvs/tools/bin/python", os.path.join(os.path.dirname(__file__), "add_channel.py"), url]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                try:
                    # Output will contain print statements, we want the last line which is JSON
                    json_str = result.stdout.strip().split('\n')[-1]
                    res = json.loads(json_str)
                    
                    if "error" in res:
                        self.send_response(400)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "error", "message": res["error"]}).encode('utf-8'))
                    else:
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "success", "message": f"Added {res.get('name', 'Channel')} ({res.get('category', 'Unknown')}) with {res.get('videos', 0)} videos!"}).encode('utf-8'))
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": f"Failed to parse backend response: {e}"}).encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()
            return
            
        if parsed_url.path == '/api/fetch_categories':
            os.system(f"/home/mladjo/.virtualenvs/tools/bin/python {os.path.join(os.path.dirname(__file__), 'fetch_categories.py')} &")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Category fetcher started in background."}).encode('utf-8'))
            return
            
        if parsed_url.path == '/api/fetch_live':
            os.system(f"/home/mladjo/.virtualenvs/tools/bin/python {os.path.join(os.path.dirname(__file__), 'fetch_live.py')} &")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Live streams fetcher started in background."}).encode('utf-8'))
            return
            
        if parsed_url.path == '/api/fetch_discovery':
            os.system(f"/home/mladjo/.virtualenvs/tools/bin/python {os.path.join(os.path.dirname(__file__), 'fetch_discovery.py')} &")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Discovery fetcher started in background."}).encode('utf-8'))
            return
            
        if parsed_url.path == '/api/fetch_trending':
            os.system(f"/home/mladjo/.virtualenvs/tools/bin/python {os.path.join(os.path.dirname(__file__), 'fetch_trending.py')} &")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Trending fetcher started in background."}).encode('utf-8'))
            return
            
        if parsed_url.path == '/api/scrape_historical':
            # Run the historical scraper for a small batch (e.g. 5)
            # Run it in the background so we don't block the UI
            os.system(f"/home/mladjo/.virtualenvs/tools/bin/python {os.path.join(os.path.dirname(__file__), 'historical_scraper.py')} 5 &")
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success", "message": "Historical scrape for 5 channels started in background."}).encode('utf-8'))
            return
            
        if parsed_url.path == '/api/load_older':
            # Run the yt-dlp deep scraper for a specific channel
            query = parse_qs(parsed_url.query)
            channel_id = query.get('channel_id', [None])[0]
            if channel_id:
                os.system(f"/home/mladjo/.virtualenvs/tools/bin/python {os.path.join(os.path.dirname(__file__), 'load_older.py')} {channel_id} &")
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "message": f"Loading older videos for channel {channel_id} in background."}).encode('utf-8'))
            else:
                self.send_response(400)
                self.end_headers()
            return
            
        self.send_response(404)
        self.end_headers()
        self.wfile.write(b"Not Found")

    def get_timeline_data(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get settings for keyword muting
        cursor.execute("SELECT value FROM settings WHERE key = 'muted_keywords'")
        row = cursor.fetchone()
        muted_keywords = []
        if row:
            try:
                muted_keywords = [k.lower() for k in json.loads(row['value']) if k.strip()]
            except json.JSONDecodeError:
                pass
        
        # Get query parameters for sorting/filtering
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        sort_by = query.get('sort', ['latest'])[0]
        category_filter = query.get('category', ['all'])[0]
        folder_filter = query.get('folder', ['all'])[0]
        
        virtual_order = """
            CASE 
                WHEN c.channel_id = 'VIRTUAL_WATCH_LATER' THEN 1
                WHEN c.channel_id = 'VIRTUAL_FAVORITES' THEN 2
                WHEN c.channel_id = 'VIRTUAL_HOME' THEN 3
                WHEN c.channel_id = 'VIRTUAL_DISCOVERY' THEN 4
                WHEN c.channel_id = 'VIRTUAL_TRENDING' THEN 5
                WHEN c.channel_id = 'VIRTUAL_LIVE' THEN 6
                ELSE 7 
            END
        """
        
        if sort_by == 'az':
            order_clause = f"ORDER BY {virtual_order}, c.name ASC"
        elif sort_by == 'most_watched':
            order_clause = f"ORDER BY {virtual_order}, c.local_views DESC, c.name ASC"
        else:
            # Sort by latest: channel with the most recent video comes first
            order_clause = f"""
                ORDER BY {virtual_order},
                (
                    SELECT MAX(v.published_at) 
                    FROM videos v 
                    WHERE v.channel_id = c.channel_id
                ) DESC
            """
            
        where_clause = "WHERE (EXISTS (SELECT 1 FROM videos v WHERE v.channel_id = c.channel_id) OR c.channel_id LIKE 'VIRTUAL_%')"
        params = []
        if category_filter != 'all':
            where_clause += " AND c.category = ?"
            params.append(category_filter)
        if folder_filter != 'all':
            where_clause += " AND c.custom_folder = ?"
            params.append(folder_filter)
            
        cursor.execute(f"""
            SELECT c.id, c.name, c.channel_id, c.url, c.local_views, c.category, c.custom_folder 
            FROM channels c
            {where_clause}
            {order_clause}
        """, params)
        channels = cursor.fetchall()
        
        result = []
        for ch in channels:
            if ch['channel_id'] == 'VIRTUAL_HOME':
                cursor.execute("""
                    SELECT v.video_id, v.title, v.published_at, v.url, v.thumbnail_url, v.is_favorite, v.is_watched, v.is_watch_later
                    FROM videos v
                    JOIN channels c ON v.channel_id = c.channel_id
                    WHERE v.is_watched = 0 AND c.channel_id NOT LIKE 'VIRTUAL_%'
                    ORDER BY (c.local_views * 10) + RANDOM() DESC
                    LIMIT 15
                """)
            elif ch['channel_id'] == 'VIRTUAL_LIVE':
                cursor.execute("""
                    SELECT video_id, title, published_at, url, thumbnail_url, is_favorite, is_watched, is_watch_later
                    FROM videos
                    WHERE channel_id = ?
                    ORDER BY is_favorite DESC, published_at DESC
                    LIMIT 100
                """, (ch['channel_id'],))
            elif ch['channel_id'] == 'VIRTUAL_WATCH_LATER':
                cursor.execute("""
                    SELECT video_id, title, published_at, url, thumbnail_url, is_favorite, is_watched, is_watch_later
                    FROM videos
                    WHERE is_watch_later = 1
                    ORDER BY published_at DESC
                """)
            elif ch['channel_id'] == 'VIRTUAL_FAVORITES':
                cursor.execute("""
                    SELECT video_id, title, published_at, url, thumbnail_url, is_favorite, is_watched, is_watch_later
                    FROM videos
                    WHERE is_favorite = 1
                    ORDER BY published_at DESC
                """)
            else:
                cursor.execute("""
                    SELECT video_id, title, published_at, url, thumbnail_url, is_favorite, is_watched, is_watch_later
                    FROM videos 
                    WHERE channel_id = ? 
                      AND (
                          published_at >= datetime('now', '-7 days') 
                          OR is_favorite = 1 
                          OR is_watch_later = 1
                          OR video_id IN (
                              SELECT video_id FROM videos 
                              WHERE channel_id = ? 
                              ORDER BY published_at DESC LIMIT 15
                          )
                      )
                    ORDER BY published_at DESC
                    LIMIT 100
                """, (ch['channel_id'], ch['channel_id']))
            
            videos = []
            for v in cursor.fetchall():
                vd = dict(v)
                title_lower = vd['title'].lower()
                muted = False
                muted_reason = ""
                for mk in muted_keywords:
                    if mk in title_lower:
                        muted = True
                        muted_reason = mk
                        break
                vd['muted'] = muted
                vd['muted_reason'] = muted_reason
                videos.append(vd)
            
            # Skip if virtual channel is empty, EXCEPT for Favorites and Watch Later
            if ch['channel_id'].startswith('VIRTUAL_') and len(videos) == 0:
                if ch['channel_id'] not in ['VIRTUAL_FAVORITES', 'VIRTUAL_WATCH_LATER']:
                    continue
                
            result.append({
                "channel_id": ch['channel_id'],
                "name": ch['name'],
                "url": ch['url'],
                "local_views": ch['local_views'],
                "category": ch['category'],
                "custom_folder": dict(ch).get('custom_folder'),
                "videos": videos
            })
            
        # Get DB stats
        cursor.execute("SELECT count(*) FROM channels WHERE channel_id IS NOT NULL")
        total_channels = cursor.fetchone()[0]
        cursor.execute("SELECT count(*) FROM videos")
        total_videos = cursor.fetchone()[0]
        
        # Get unique categories
        cursor.execute("SELECT DISTINCT category FROM channels WHERE category IS NOT NULL ORDER BY category ASC")
        categories = [row[0] for row in cursor.fetchall()]
        
        # Get unique custom folders
        cursor.execute("SELECT DISTINCT custom_folder FROM channels WHERE custom_folder IS NOT NULL AND custom_folder != '' ORDER BY custom_folder ASC")
        custom_folders = [row[0] for row in cursor.fetchall()]
            
        conn.close()
        return {
            "stats": {"channels": total_channels, "videos": total_videos},
            "categories": categories,
            "custom_folders": custom_folders,
            "timeline": result
        }

def run():
    server_address = ('', PORT)
    httpd = HTTPServer(server_address, YTDashboardHandler)
    print(f"Starting YT Dashboard server on http://localhost:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    print("Server stopped.")

if __name__ == '__main__':
    run()
