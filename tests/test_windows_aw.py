import sqlite3
import json
import datetime

db_path = "/media/linuxayan/0E3A629E3A628297/Users/baidy/AppData/Local/activitywatch/activitywatch/aw-server/peewee-sqlite.v2.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Find the window watcher bucket
    cursor.execute("SELECT key, id FROM bucketmodel WHERE id LIKE '%window%'")
    buckets = cursor.fetchall()
    print("[*] Found Window Buckets:")
    window_bucket_key = None
    for b_key, b_id in buckets:
        print(f"  - Key: {b_key}, ID: {b_id}")
        if "aw-watcher-window" in b_id:
            window_bucket_key = b_key
            
    if not window_bucket_key:
        print("[-] Could not find an aw-watcher-window bucket.")
        exit(1)
        
    # 2. Get today's events
    today_str = datetime.date.today().isoformat()
    query = "SELECT timestamp, duration, datastr FROM eventmodel WHERE bucket_id = ? AND timestamp LIKE ? ORDER BY timestamp DESC LIMIT 20"
    cursor.execute(query, (window_bucket_key, f"{today_str}%"))
    events = cursor.fetchall()
    
    print(f"\n[*] Latest 20 Events from Windows for {today_str}:")
    for ts, dur, datastr in events:
        data = json.loads(datastr)
        app = data.get("app", "Unknown")
        title = data.get("title", "Unknown")
        print(f"[{ts}] ({dur}s) {app}: {title}")
        
    conn.close()
    
except Exception as e:
    print(f"[-] Error querying Windows DB: {e}")
