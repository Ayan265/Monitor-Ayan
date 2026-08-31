import json
import datetime
from collections import defaultdict

mobile_file = "/home/linuxayan/A/activity watch"
today_str = str(datetime.date.today())

try:
    with open(mobile_file, 'r', encoding='utf-8') as mf:
        m_data = json.load(mf)
    
    buckets = m_data.get("buckets", {})
    android_bucket = None
    for b_name in buckets:
        if "aw-watcher-android" in b_name:
            android_bucket = buckets[b_name]
            break
            
    app_times = defaultdict(float)
    
    if android_bucket:
        for event in android_bucket.get("events", []):
            timestamp_str = event.get("timestamp", "")
            if timestamp_str.startswith(today_str):
                duration = int(event.get("duration", 0))
                if duration > 0:
                    # Pure raw app name straight from the JSON
                    app_name = event.get("data", {}).get("app", "Unknown App")
                    app_times[app_name] += duration
                    
    print(f"=== Raw Mobile Data for {today_str} ===")
    sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)
    
    for app, secs in sorted_apps:
        mins = secs / 60
        if mins >= 0.5:
            print(f" - {app}: {mins:.1f} minutes")
            
except Exception as e:
    print(f"[-] Error: {e}")
