#!/usr/bin/env python3
# DESC: Imports channels from subscriptions.csv into the database
import csv
import os
from db import get_db_connection

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "subscriptions.csv")

def import_channels():
    if not os.path.exists(CSV_PATH):
        print(f"Error: {CSV_PATH} not found.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader, None)
        
        count = 0
        for row in reader:
            if not row:
                continue
            
            # The last line might have "debugger eval code..." from the console
            if "debugger eval code" in row[0]:
                continue
                
            if len(row) == 1:
                parts = row[0].rsplit(',', 1)
                if len(parts) == 2:
                    name, url = parts[0].strip(), parts[1].strip()
                else:
                    continue
            elif len(row) >= 2:
                name, url = row[0].strip(), row[1].strip()
            else:
                continue
            
            try:
                cursor.execute(
                    "INSERT OR IGNORE INTO channels (name, url) VALUES (?, ?)",
                    (name, url)
                )
                if cursor.rowcount > 0:
                    count += 1
            except Exception as e:
                print(f"Error inserting {name}: {e}")
                
    conn.commit()
    conn.close()
    print(f"Successfully imported {count} new channels.")

if __name__ == "__main__":
    import_channels()
