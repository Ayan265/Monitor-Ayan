import csv
import re
from collections import defaultdict
from datetime import date

csv_file = "/home/linuxayan/Desktop/Monitor_ayan/data/activity_history.csv"
today_str = str(date.today())

app_times = defaultdict(int)
total_time = 0

def clean_title(title):
    title = title.lower().strip()
    
    # 1. Strip browser suffixes
    for suffix in [" — mozilla firefox", " - mozilla firefox", " - google chrome", " - brave", " — brave", " - chromium", " - text editor"]:
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
            
    # 2. Strip notification counts like "(28) " or "(1) "
    title = re.sub(r'^\(\d+\)\s*', '', title)
    
    # 3. Intelligent Grouping (Fuzzy matching for common tasks)
    if "whatsapp" in title: return "WhatsApp"
    if "youtube" in title: return "YouTube"
    if "chatgpt" in title: return "ChatGPT"
    if "monitor_ayan" in title or "antigravity" in title: return "Coding (Accountability Monitor)"
    if "apollo" in title: return "Apollo Research"
    if "syncthing" in title: return "Syncthing Settings"
    if "activitywatch" in title or "activity watch" in title: return "ActivityWatch Settings"
    if "localsend" in title: return "LocalSend"
    
    # Capitalize cleanly if no group matched
    return title.title()

try:
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None) # skip header
        for row in reader:
            if len(row) >= 3 and row[0].startswith(today_str):
                raw_title = row[1]
                
                # Skip junk
                if not raw_title or "desktop icons" in raw_title.lower() or "gnome-shell" in raw_title.lower():
                    continue
                    
                duration = int(row[2])
                if duration <= 0: continue
                
                total_time += duration
                grouped_title = clean_title(raw_title)
                app_times[grouped_title] += duration

    print(f"Total Laptop Screen Time: {total_time / 60:.1f} minutes\n")
    print("Filtered Breakdown:")
    
    sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)
    for app, seconds in sorted_apps:
        mins = seconds / 60
        if mins >= 0.5: # Only show things used for at least 30 seconds
            print(f" - {app}: {mins:.1f} minutes")

except Exception as e:
    print(f"Error: {e}")
