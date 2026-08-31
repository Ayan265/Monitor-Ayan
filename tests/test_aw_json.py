import json
from collections import defaultdict
from datetime import datetime

file_path = "/home/linuxayan/Downloads/aw-buckets-export.json"

try:
    with open(file_path, 'r') as f:
        data = json.load(f)
        
    buckets = data.get("buckets", {})
    android_bucket = None
    
    # Find the android bucket dynamically
    for b_name in buckets:
        if "aw-watcher-android" in b_name:
            android_bucket = buckets[b_name]
            break
            
    if not android_bucket:
        print("[-] Could not find android bucket in JSON.")
        exit(1)
        
    events = android_bucket.get("events", [])
    print(f"[*] Found {len(events)} mobile events.")
    
    app_times = defaultdict(float)
    
    for event in events:
        duration_seconds = event.get("duration", 0)
        app_name = event.get("data", {}).get("app", "Unknown App")
        
        # Only count if duration is positive
        if duration_seconds > 0:
            app_times[app_name] += duration_seconds
            
    print("\n=== Mobile App Usage Summary ===")
    sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)
    
    for app, secs in sorted_apps:
        mins = secs / 60
        if mins >= 1:
            print(f" - {app}: {mins:.1f} minutes")
            
except Exception as e:
    print(f"[-] Error: {e}")
