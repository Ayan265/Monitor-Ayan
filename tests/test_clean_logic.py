import csv
import re
import datetime

LOG_FILE = "/home/linuxayan/Desktop/Monitor_ayan/data/activity_history.csv"
today_str = str(datetime.date.today())

pc_app_times = {}

with open(LOG_FILE, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    next(reader, None) # skip header
    for row in reader:
        if len(row) >= 3 and row[0].startswith(today_str):
            title = row[1].strip()
            if not title or "desktop icons" in title.lower() or "gnome-shell" in title.lower():
                continue
            duration = int(row[2])
            clean_title = title
            
            # Remove ugly browser suffixes
            for suffix in [" — mozilla firefox", " - mozilla firefox", " - google chrome", " - brave", " — brave", " - chromium", " - text editor"]:
                if clean_title.lower().endswith(suffix):
                    clean_title = clean_title[:-len(suffix)]
                    
            # Strip notification counts
            clean_title = re.sub(r'^\(\d+\)\s*', '', clean_title.strip())
            
            # Professional Title Case
            clean_title = clean_title.strip().title()
            
            # Simplify complex titles
            if " - " in clean_title:
                clean_title = clean_title.split(" - ")[-1].strip()
            elif " | " in clean_title:
                clean_title = clean_title.split(" | ")[-1].strip()
                
            short_title = clean_title[:30] + "..." if len(clean_title) > 30 else clean_title
            pc_app_times[short_title] = pc_app_times.get(short_title, 0) + duration

sorted_pc = sorted(pc_app_times.items(), key=lambda x: x[1], reverse=True)
for app, secs in sorted_pc:
    print(f"{app} ({secs//60} mins)")
