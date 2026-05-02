# YouTube Dashboard

A privacy-first, standalone local web dashboard offering a timeline "Sashimi" view of your YouTube subscriptions.

## 🛡️ Privacy-First Browsing

**Option 2: Local Click Tracking (The Forward-Looking, Privacy-First Way)**

When you browse YouTube directly, Google tracks every thumbnail you hover over, every channel you scroll past, and the exact order of your browsing behavior. They use this to profile you and adjust their algorithmic manipulation.

**With this Dashboard, Google is blind to your browsing behavior.**

- **They do not know** what channels you scrolled past.
- **They do not know** what order you view your subscriptions in.
- **They do not know** what you searched for on your own dashboard.
- **They only get a ping** at the exact moment you hit "Play."

We use local SQLite databases to track your watch history and click rates. We then use this data to sort your channels by **"Most Watched"** entirely locally, meaning you get the benefit of algorithmic personalization without surrendering your behavioral data to Big Tech.

## ✨ Features

- **No API Keys Required:** Uses anonymous YouTube RSS feeds for continuous, fast updates without rate limits.
- **Deep Historical Scraping:** Uses `yt-dlp` for on-demand fetches of older videos per channel.
- **Local Watch History & Click Tracking:** Automatically sorts your favorite channels to the top based on how often you watch them.
- **TV Guide Categories:** Extracts official YouTube genres (News, Science, Music) to let you instantly filter your timeline.
- **7-Day Retention & Favorites:** Videos stay on your timeline for 7 days. Click the "Star" icon to save a video forever.
- **Visual Progress:** See exactly which videos you've already watched with a clear red progress indicator.
- **Live Search & Sorting:** Instantly filter channels by name or sort by "Latest Upload", "Most Watched", or "A-Z".
- **Completely Local & Fast:** Built with pure Python standard library (`http.server`) and vanilla HTML/JS/CSS.

### 🤖 Privacy-First Algorithmic Rows
By default, the dashboard pins 4 dynamically generated rows to the top of your timeline to mimic YouTube's discovery features without compromising your data:
1. **Recommended For You:** Fully local! It securely recommends unwatched videos from your personal most-viewed channels.
2. **New to You (Discovery):** Looks at the topics of videos you recently watched and anonymously searches YouTube for brand new channels discussing those exact same topics.
3. **YouTube Trending:** Uses `yt-dlp` to anonymously scrape the default YouTube trending page for generic viral videos.
4. **Top Live Streams:** A dedicated row for current global YouTube Live broadcasts, updatable on demand.

## 🚀 Setup & Usage

### ⏱️ Important Note on Wait Times (Anti-Ban Protection)
To ensure Google doesn't detect you as a bot and block your IP, the scraper scripts are intentionally designed to run *slowly*:
- **Initial Historical Scrape:** Takes ~2 seconds per channel. If you have 600 subscriptions, expect this to take ~20 minutes.
- **Genre/Category Scan (`yt-dlp`):** Takes ~2 to 5 seconds per channel. For 600 subscriptions, this will take ~30-45 minutes.

**All scripts are fully resumable.** If you close the terminal or interrupt a scan, you can run the command again later, and it will pick up exactly where it left off, skipping the channels it has already processed.

1. **Install Dependencies**
   Ensure you have Python 3 installed. You will also need `yt-dlp` installed globally.
   ```bash
   pip install yt-dlp
   ```

2. **Initialize Database**
   ```bash
   python projects/yt_dashboard/db.py
   ```

3. **Import Subscriptions**
   Export your YouTube subscriptions (or use a browser script to grab them) to a `subscriptions.csv` file, then run:
   ```bash
   python projects/yt_dashboard/import_channels.py
   ```

4. **Run Initial Scraper**
   This will find the `channel_id` for your subscriptions.
   ```bash
   python projects/yt_dashboard/historical_scraper.py
   ```

5. **Import Watch History (Optional but Recommended)**
   To instantly train the "Most Watched" algorithm and mark your previously watched videos:
   - Go to Google Takeout (takeout.google.com).
   - **CRITICAL (For Brand Accounts):** Click your profile picture in the top right and ensure you have selected the specific Brand Account that holds your subscriptions. If it's missing, go to `myaccount.google.com/brandaccounts` first to trigger the Takeout from the account's dashboard.
   - Deselect everything, select only "YouTube and YouTube Music".
   - Click "Multiple Formats" and ensure History is set to **JSON**.
   - Click "All YouTube data included", deselect all, and select only **history**.
   - Export, extract, and move `watch-history.json` to `projects/yt_dashboard/data/`.
   - Run the import script:
     ```bash
     python projects/yt_dashboard/import_watch_history.py
     ```

6. **Start the Dashboard**
   ```bash
   python projects/yt_dashboard/app.py
   ```
   Open your browser to `http://localhost:8080`

7. **Keep It Updated**
   You can click **"Update from RSS"** in the UI, or set up a cron job to run:
   ```bash
   python projects/yt_dashboard/rss_poller.py
   ```

## 🏗️ Architecture

- `app.py`: Lightweight Python web server exposing the JSON API.
- `db.py`: SQLite connection and schema definition.
- `rss_poller.py`: Fast, key-less XML parser that fetches the latest 15 videos per channel. Priority is given to your most-watched channels.
- `historical_scraper.py`: Extracts raw `UC...` channel IDs from URLs.
- `fetch_categories.py`: Background job using `yt-dlp` to gently extract official YouTube genres (News, Science, etc) for your channels.
- `load_older.py`: Deep-fetches up to 50 videos at a time using `yt-dlp`.

## 🤝 Open Source

Feel free to fork, modify, and build upon this structure. It's designed to be a transparent alternative to the attention-economy algorithms.
