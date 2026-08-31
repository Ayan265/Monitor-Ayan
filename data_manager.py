import time
import subprocess
import csv
import datetime
import os
import sys
import logging
import json
import re
import threading
from config import (
    RULES,
    SUMMARY_WHATSAPP_TARGETS, ALERT_WHATSAPP_TARGETS, ALERT_IG_USERNAMES,
    SCRIPT_DIR, LOG_FILE, MONITOR_LOG, STATS_FILE, STREAK_FILE, QUEUE_FILE,
    IDLE_THRESHOLD_SECS, GEMINI_API_KEY,
    log
)

# Import get_logical_today from web_server to avoid circular imports
from web_server import get_logical_today


def log_to_csv(title, duration_seconds):
    """Saves a permanent record of what you did and for how long."""
    if not title:
        return
        
    title_lower = title.lower()
    # Ignore background desktop environments so suspend time isn't logged
    if "desktop icons" in title_lower or "gnome-shell" in title_lower:
        return
        
    try:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([now, title, duration_seconds])
    except Exception as e:
        log.error(f"CSV write failed: {e}")


def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                data = json.load(f)
                saved_date = data.get("date")
                time_spent = data.get("time_spent", {category: 0 for category in RULES.keys()})
                
                alert_level = data.get("alert_level", {})
                if not alert_level and "alert_sent" in data:
                    old_alert = data.get("alert_sent", {})
                    alert_level = {k: (1 if v else 0) for k, v in old_alert.items()}
                    
                for category in RULES.keys():
                    if category not in alert_level:
                        alert_level[category] = 0
                        
                return time_spent, alert_level, saved_date
        except Exception:
            pass
    return {category: 0 for category in RULES.keys()}, {category: 0 for category in RULES.keys()}, None


def save_stats(time_spent, alert_level):
    try:
        tmp_file = STATS_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump({
                "date": str(get_logical_today()),
                "time_spent": time_spent,
                "alert_level": alert_level
            }, f)
        os.replace(tmp_file, STATS_FILE)
    except Exception:
        pass


def calculate_focus_score(prod, strug, prom_made, prom_kept):
    total_sessions = prod + strug
    if total_sessions == 0:
        return 0
        
    focus_rate = prod / total_sessions
    
    if prom_made == 0:
        score = focus_rate
    else:
        integrity_rate = prom_kept / prom_made
        score = (focus_rate * 0.7) + (integrity_rate * 0.3)
        
    return round(score * 100)


def get_resort_to_grow_stats(target_date_str=None):
    history_file = os.path.expanduser("~/.accountability_history.json")
    if not os.path.exists(history_file):
        return None
        
    try:
        with open(history_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if target_date_str:
            t_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        else:
            t_date = get_logical_today()
            
        today_str = str(t_date)
        yesterday_str = str(t_date - datetime.timedelta(days=1))
        
        stats = {
            today_str: {"prod": 0, "strug": 0, "probs": {}, "prom_made": 0, "prom_kept": 0},
            yesterday_str: {"prod": 0, "strug": 0, "probs": {}, "prom_made": 0, "prom_kept": 0}
        }
        
        for entry in data:
            ts = entry.get("timestamp", "")
            date_key = ts[:10]
            
            if date_key in stats:
                etype = entry.get("entry_type")
                if etype == "productive":
                    stats[date_key]["prod"] += 1
                elif etype == "struggled":
                    stats[date_key]["strug"] += 1
                    prob = entry.get("problem", "unknown")
                    if prob:
                        stats[date_key]["probs"][prob] = stats[date_key]["probs"].get(prob, 0) + 1
                elif etype == "promise_review" and "promise_honored" in entry:
                    stats[date_key]["prom_made"] += 1
                    if entry.get("promise_honored") is True:
                        stats[date_key]["prom_kept"] += 1
                        
        td = stats[today_str]
        yd = stats[yesterday_str]
        
        td_score = calculate_focus_score(td["prod"], td["strug"], td["prom_made"], td["prom_kept"])
        yd_score = calculate_focus_score(yd["prod"], yd["strug"], yd["prom_made"], yd["prom_kept"])
        
        return {
            "today": td,
            "yesterday": yd,
            "today_score": td_score,
            "yesterday_score": yd_score
        }
    except Exception as e:
        log.error(f"Failed to parse resort to grow insights: {e}")
        return None


def get_streak():
    if os.path.exists(STREAK_FILE):
        try:
            with open(STREAK_FILE, 'r') as f:
                return json.load(f).get("streak", 0)
        except Exception:
            pass
    return 0


def update_streak(score):
    streak_data = {"streak": 0, "last_date": ""}
    if os.path.exists(STREAK_FILE):
        try:
            with open(STREAK_FILE, 'r') as f:
                streak_data = json.load(f)
        except Exception:
            pass
            
    today = str(get_logical_today())
    if streak_data.get("last_date") == today:
        return streak_data.get("streak", 0) # Already updated today
        
    streak = streak_data.get("streak", 0)
    if score >= 70:
        streak += 1
    else:
        streak = 0
        
    try:
        with open(STREAK_FILE, 'w') as f:
            json.dump({"streak": streak, "last_date": today}, f)
    except Exception:
        pass
    return streak


def get_top_time_sinks(target_date_str=None):
    today_str = target_date_str if target_date_str else str(get_logical_today())
    
    target_dt = datetime.datetime.strptime(today_str, "%Y-%m-%d").date()
    prev_str = str(target_dt - datetime.timedelta(days=1))
    
    def is_in_logical_day(ts_str):
        if len(ts_str) < 19: return False
        date_part = ts_str[:10]
        time_part = ts_str[11:19]
        if date_part == today_str and time_part < "22:00:00":
            return True
        if date_part == prev_str and time_part >= "22:00:00":
            return True
        return False

    pc_total_time = 0
    mobile_total_time = 0
    pc_app_times = {}
    mobile_app_times = {}
    wasted_breakdown = {'bad_habit': {}, 'anime_manga': {}}
    
    if not os.path.exists(LOG_FILE):
        return 0, 0, [], [], {}
        
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None) # skip header
            for row in reader:
                if len(row) >= 3 and is_in_logical_day(row[0]):
                    try:
                        title = row[1].strip()
                        if not title:
                            continue
                        if "desktop icons" in title.lower() or "gnome-shell" in title.lower():
                            continue
                        
                        duration = int(row[2])
                        pc_total_time += duration
                        
                        clean_title = title
                        
                        # Remove ugly browser suffixes
                        for suffix in [" — mozilla firefox", " - mozilla firefox", " - google chrome", " - brave", " — brave", " - chromium", " - text editor"]:
                            if clean_title.lower().endswith(suffix):
                                clean_title = clean_title[:-len(suffix)]
                                
                        # Strip notification counts like "(28) " or "(1) "
                        clean_title = re.sub(r'^\(\d+\)\s*', '', clean_title.strip())
                                
                        # Professional Title Case
                        clean_title = clean_title.strip().title()
                        
                        # Simplify complex titles (like IDE files or web pages) by taking the first and last segments
                        if " - " in clean_title:
                            parts = [p.strip() for p in clean_title.split(" - ")]
                            if len(parts) >= 2:
                                clean_title = f"{parts[0]}: {parts[-1]}"
                        elif " | " in clean_title:
                            parts = [p.strip() for p in clean_title.split(" | ")]
                            if len(parts) >= 2:
                                clean_title = f"{parts[0]}: {parts[-1]}"
                        
                        # Apply smart grouping logic
                        clean_title = simplify_title(clean_title)
                            
                        # Cap length for whatsapp formatting gracefully
                        short_title = clean_title[:60] + "..." if len(clean_title) > 60 else clean_title
                        pc_app_times[short_title] = pc_app_times.get(short_title, 0) + duration
                        
                        # Track specifically what caused wasted time
                        title_lower = title.lower()
                        for category in ['bad_habit', 'anime_manga']:
                            if any(kw in title_lower for kw in RULES[category]["keywords"]):
                                wasted_breakdown[category][short_title] = wasted_breakdown[category].get(short_title, 0) + duration
                    except Exception:
                        pass
                        
        # --- Mobile Data Integration ---
        mobile_file = "/home/linuxayan/A/activity watch"
        if os.path.exists(mobile_file):
            try:
                with open(mobile_file, 'r', encoding='utf-8') as mf:
                    m_data = json.load(mf)
                
                buckets = m_data.get("buckets", {})
                android_bucket = None
                for b_name in buckets:
                    if "aw-watcher-android" in b_name:
                        android_bucket = buckets[b_name]
                        break
                        
                if android_bucket:
                    for event in android_bucket.get("events", []):
                        # The timestamp is ISO format like "2026-06-28T07:52:20..."
                        timestamp_str = event.get("timestamp", "")
                        if is_in_logical_day(timestamp_str):
                            duration = int(event.get("duration", 0))
                            if duration > 0:
                                app_name = event.get("data", {}).get("app", "Unknown App").strip().title()
                                
                                # Ignore father's apps
                                if any(ignore_app in app_name.lower() for ignore_app in ["groww", "axis mobile"]):
                                    continue
                                
                                # Apply smart grouping logic
                                app_name = simplify_title(app_name)
                                
                                # Cap length gracefully
                                short_title = app_name[:45] + "..." if len(app_name) > 45 else app_name
                                
                                mobile_total_time += duration
                                mobile_app_times[short_title] = mobile_app_times.get(short_title, 0) + duration
                                
                                # Track specifically what caused wasted time
                                title_lower = app_name.lower()
                                for category in ['bad_habit', 'anime_manga']:
                                    if any(kw in title_lower for kw in RULES[category]["keywords"]):
                                        wasted_breakdown[category][short_title] = wasted_breakdown[category].get(short_title, 0) + duration
            except Exception as e:
                log.error(f"Failed to parse mobile JSON for time sinks: {e}")

        # --- Windows Data Integration ---
        windows_drive = "/media/linuxayan/0E3A629E3A628297"
        windows_db = f"{windows_drive}/Users/baidy/AppData/Local/activitywatch/activitywatch/aw-server/peewee-sqlite.v2.db"
        if not os.path.exists(windows_drive):
            try:
                subprocess.run(["udisksctl", "mount", "-b", "/dev/nvme0n1p3"], capture_output=True)
            except Exception:
                pass
                
        if os.path.exists(windows_db):
            try:
                import sqlite3
                conn = sqlite3.connect(windows_db)
                cursor = conn.cursor()
                cursor.execute("SELECT key, id FROM bucketmodel WHERE id LIKE '%window%' OR id LIKE '%web-firefox%'")
                buckets = cursor.fetchall()
                
                window_bucket_key = next((b_key for b_key, b_id in buckets if "aw-watcher-window" in b_id), None)
                firefox_bucket_key = next((b_key for b_key, b_id in buckets if "aw-watcher-web-firefox" in b_id), None)
                
                if window_bucket_key:
                    cursor.execute("SELECT duration, datastr, timestamp FROM eventmodel WHERE bucket_id = ? AND (timestamp LIKE ? OR timestamp LIKE ?)", (window_bucket_key, f"{today_str}%", f"{prev_str}%"))
                    for dur, datastr, ts in cursor.fetchall():
                        if not is_in_logical_day(ts): continue
                        dur = int(dur)
                        if dur > 0:
                            data = json.loads(datastr)
                            app_name = data.get("app", "Unknown").strip().title()
                            
                            # Prevent double counting Firefox since we use the web watcher
                            if app_name.lower() in ["firefox.exe", "firefox", "mozilla firefox"]:
                                continue
                                
                            app_name = simplify_title(app_name)
                            
                            short_title = f"[Win] {app_name[:40]}" + "..." if len(app_name) > 40 else f"[Win] {app_name}"
                            pc_total_time += dur
                            pc_app_times[short_title] = pc_app_times.get(short_title, 0) + dur
                            title_lower = app_name.lower()
                            for category in ['bad_habit', 'anime_manga']:
                                if any(kw in title_lower for kw in RULES[category]["keywords"]):
                                    wasted_breakdown[category][short_title] = wasted_breakdown[category].get(short_title, 0) + dur

                if firefox_bucket_key:
                    cursor.execute("SELECT duration, datastr, timestamp FROM eventmodel WHERE bucket_id = ? AND (timestamp LIKE ? OR timestamp LIKE ?)", (firefox_bucket_key, f"{today_str}%", f"{prev_str}%"))
                    for dur, datastr, ts in cursor.fetchall():
                        if not is_in_logical_day(ts): continue
                        dur = int(dur)
                        if dur > 0:
                            data = json.loads(datastr)
                            title = data.get("title", "Unknown").strip().title()
                            title = simplify_title(title)
                            url = data.get("url", "Unknown")
                            short_title = f"[Win Firefox] {title[:40]}" + "..." if len(title) > 40 else f"[Win Firefox] {title}"
                            pc_total_time += dur
                            pc_app_times[short_title] = pc_app_times.get(short_title, 0) + dur
                            title_lower = title.lower()
                            url_lower = url.lower()
                            for category in ['bad_habit', 'anime_manga']:
                                if any(kw in title_lower or kw in url_lower for kw in RULES[category]["keywords"]):
                                    wasted_breakdown[category][short_title] = wasted_breakdown[category].get(short_title, 0) + dur
                conn.close()
            except Exception as e:
                log.error(f"Failed to parse Windows SQLite for time sinks: {e}")

        sorted_pc = sorted(pc_app_times.items(), key=lambda x: x[1], reverse=True)
        sorted_mobile = sorted(mobile_app_times.items(), key=lambda x: x[1], reverse=True)
        
        # Filter out negligible apps to save token count for AI
        top_pc = [x for x in sorted_pc if x[1] > 60]
        top_mobile = [x for x in sorted_mobile if x[1] > 60]
        
        # Sort the wasted breakdowns too
        for cat in wasted_breakdown:
            wasted_breakdown[cat] = sorted(wasted_breakdown[cat].items(), key=lambda x: x[1], reverse=True)
            
        return pc_total_time, mobile_total_time, sorted_pc[:10], sorted_mobile[:10], wasted_breakdown
    except Exception as e:
        log.error(f"Failed to parse CSV for time sinks: {e}")
        return 0, 0, [], [], {}


def simplify_title(title):
    t = title.lower().strip()
    
    # Remove notification counts like (28) 
    t = re.sub(r'^\(\d+\)\s*', '', t)
    
    # Intelligently group YouTube
    if "youtube" in t:
        # Group Shorts together
        if "#shorts" in t or "shorts -" in t or "shorts" in t.split():
            return "YouTube Shorts"
        # Group generic YouTube homepage/feed browsing
        if t == "youtube" or t == "youtube - mozilla firefox" or t == "youtube — mozilla firefox":
            return "YouTube (Browsing)"
        # Keep specific video titles intact so Gemini knows WHAT you are watching
        return title
        
    if "whatsapp" in t: return "WhatsApp"
    if "instagram" in t: return "Instagram"
    if "google search" in t: return "Google Search"
    if "vs code" in t or "visual studio" in t: return "VS Code"
    if "antigravity" in t: return "Antigravity IDE"
    if "terminal" in t: return "Terminal"
    if "chatgpt" in t or "gemini" in t or "claude" in t: return "AI Tools"
    if "github" in t: return "GitHub"
    return title


def cleanup_old_data():
    """Removes entries older than 14 days from activity_history.csv to keep parsing fast."""
    if not os.path.exists(LOG_FILE):
        return
        
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=14)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(LOG_FILE, 'r') as f:
            lines = f.readlines()
            
        if not lines: return
            
        header = lines[0]
        valid_lines = [header]
        
        for line in lines[1:]:
            try:
                parts = line.split(",", 1)
                if len(parts) >= 1:
                    timestamp_str = parts[0]
                    if timestamp_str >= cutoff_str:
                        valid_lines.append(line)
            except Exception:
                pass
                
        if len(valid_lines) < len(lines):
            with open(LOG_FILE, 'w') as f:
                f.writelines(valid_lines)
            print(f"[*] Cleaned up {len(lines) - len(valid_lines)} old entries from {LOG_FILE}")
            
    except Exception as e:
        log.error(f"Failed to cleanup old data: {e}")


def get_weekly_time_sinks():
    """Aggregates raw CSV and Mobile JSON data for the past 7 days."""
    cutoff_date = datetime.datetime.now() - datetime.timedelta(days=7)
    cutoff_str = cutoff_date.strftime("%Y-%m-%d 00:00:00")
    
    pc_total_time = 0
    pc_app_times = {}
    
    # 1. Parse PC CSV
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, 'r') as f:
                reader = csv.reader(f)
                next(reader, None) # Skip header
                for row in reader:
                    if len(row) >= 3:
                        timestamp, title, duration = row[0], row[1], int(row[2])
                        if timestamp >= cutoff_str:
                            pc_total_time += duration
                            
                            clean_title = title.lower()
                            for suffix in [" - google chrome", " — mozilla firefox", " - brave", " - opera", " - youtube"]:
                                clean_title = clean_title.replace(suffix, "")
                            if clean_title.startswith("(") and ")" in clean_title:
                                clean_title = clean_title.split(")", 1)[-1].strip()
                            clean_title = clean_title.strip().title()
                            
                            if " - " in clean_title:
                                parts = [p.strip() for p in clean_title.split(" - ")]
                                if len(parts) >= 2:
                                    clean_title = f"{parts[0]}: {parts[-1]}"
                            elif " | " in clean_title:
                                parts = [p.strip() for p in clean_title.split(" | ")]
                                if len(parts) >= 2:
                                    clean_title = f"{parts[0]}: {parts[-1]}"
                                    
                            short_title = clean_title[:40] + "..." if len(clean_title) > 40 else clean_title
                            pc_app_times[short_title] = pc_app_times.get(short_title, 0) + duration
    except Exception as e:
        log.error(f"Failed to parse PC weekly CSV: {e}")

    # 2. Parse Mobile JSONs (All files modified in the last 7 days)
    mobile_total_time = 0
    mobile_app_times = {}
    
    try:
        mobile_sync_dir = os.path.expanduser("~/A/activity watch")
        if os.path.exists(mobile_sync_dir):
            if os.path.isdir(mobile_sync_dir):
                for filename in os.listdir(mobile_sync_dir):
                    if filename.endswith(".json"):
                        file_path = os.path.join(mobile_sync_dir, filename)
                        file_mod_time = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mod_time >= cutoff_date:
                            with open(file_path, 'r') as f:
                                data = json.load(f)
                            for event in data:
                                app_name = event.get('app_name', 'Unknown')
                                duration = int(event.get('duration_seconds', 0))
                                
                                if duration > 0 and app_name.lower() not in ["system ui", "unknown"]:
                                    # Ignore father's apps
                                    if any(ignore_app in app_name.lower() for ignore_app in ["groww", "axis mobile"]):
                                        continue
                                        
                                    mobile_total_time += duration
                                    short_title = app_name[:40].title()
                                    mobile_app_times[short_title] = mobile_app_times.get(short_title, 0) + duration
            else:
                with open(mobile_sync_dir, 'r', encoding='utf-8') as mf:
                    m_data = json.load(mf)
                buckets = m_data.get("buckets", {})
                android_bucket = None
                for b_name in buckets:
                    if "aw-watcher-android" in b_name:
                        android_bucket = buckets[b_name]
                        break
                if android_bucket:
                    for event in android_bucket.get("events", []):
                        timestamp_str = event.get("timestamp", "")
                        try:
                            # Strip Z or offset to parse date
                            t_str = timestamp_str.replace("Z", "").split(".")[0]
                            event_date = datetime.datetime.strptime(t_str, "%Y-%m-%dT%H:%M:%S")
                            if event_date >= cutoff_date:
                                duration = int(event.get("duration", 0))
                                if duration > 0:
                                    app_name = event.get("data", {}).get("app", "Unknown App").strip().title()
                                    if any(ignore_app in app_name.lower() for ignore_app in ["groww", "axis mobile"]):
                                        continue
                                    app_name = simplify_title(app_name)
                                    short_title = app_name[:40].title()
                                    mobile_total_time += duration
                                    mobile_app_times[short_title] = mobile_app_times.get(short_title, 0) + duration
                        except Exception:
                            pass
    except Exception as e:
        log.error(f"Failed to parse Mobile weekly JSON: {e}")

    # 3. Parse Windows SQLite (7 days)
    windows_drive = "/media/linuxayan/0E3A629E3A628297"
    windows_db = f"{windows_drive}/Users/baidy/AppData/Local/activitywatch/activitywatch/aw-server/peewee-sqlite.v2.db"
    if not os.path.exists(windows_drive):
        try:
            subprocess.run(["udisksctl", "mount", "-b", "/dev/nvme0n1p3"], capture_output=True)
        except Exception:
            pass

    if os.path.exists(windows_db):
        try:
            import sqlite3
            conn = sqlite3.connect(windows_db)
            cursor = conn.cursor()
            cursor.execute("SELECT key, id FROM bucketmodel WHERE id LIKE '%window%' OR id LIKE '%web-firefox%'")
            buckets = cursor.fetchall()
            
            window_bucket_key = next((b_key for b_key, b_id in buckets if "aw-watcher-window" in b_id), None)
            firefox_bucket_key = next((b_key for b_key, b_id in buckets if "aw-watcher-web-firefox" in b_id), None)
            
            if window_bucket_key:
                cursor.execute("SELECT duration, datastr FROM eventmodel WHERE bucket_id = ? AND timestamp >= ?", (window_bucket_key, cutoff_date.isoformat()))
                for dur, datastr in cursor.fetchall():
                    dur = int(dur)
                    if dur > 0:
                        data = json.loads(datastr)
                        app_name = data.get("app", "Unknown").strip().title()
                        short_title = f"[Win] {app_name[:34]}" + "..." if len(app_name) > 34 else f"[Win] {app_name}"
                        pc_total_time += dur
                        pc_app_times[short_title] = pc_app_times.get(short_title, 0) + dur
                        
            if firefox_bucket_key:
                cursor.execute("SELECT duration, datastr FROM eventmodel WHERE bucket_id = ? AND timestamp >= ?", (firefox_bucket_key, cutoff_date.isoformat()))
                for dur, datastr in cursor.fetchall():
                    dur = int(dur)
                    if dur > 0:
                        data = json.loads(datastr)
                        title = data.get("title", "Unknown").strip().title()
                        short_title = f"[Win Firefox] {title[:34]}" + "..." if len(title) > 34 else f"[Win Firefox] {title}"
                        pc_total_time += dur
                        pc_app_times[short_title] = pc_app_times.get(short_title, 0) + dur
                        
            conn.close()
        except Exception as e:
            log.error(f"Failed to parse Windows SQLite for weekly time sinks: {e}")

    sorted_pc = sorted(pc_app_times.items(), key=lambda x: x[1], reverse=True)
    sorted_pc = [(app, secs) for app, secs in sorted_pc if secs >= 300] # Min 5 mins
    
    sorted_mobile = sorted(mobile_app_times.items(), key=lambda x: x[1], reverse=True)
    sorted_mobile = [(app, secs) for app, secs in sorted_mobile if secs >= 300]
    
    return pc_total_time, mobile_total_time, sorted_pc[:20], sorted_mobile[:20]


def update_and_get_daily_scores(target_date_str, score):
    import json
    import os
    
    history_file = "/home/linuxayan/Desktop/Monitor_ayan/data/daily_scores.json"
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except Exception:
            history = []
            
    found = False
    for item in history:
        if item['date'] == target_date_str:
            item['score'] = score
            found = True
            break
            
    if not found:
        history.append({'date': target_date_str, 'score': score})
        
    history = sorted(history, key=lambda x: x['date'])
    
    current_price = 100.0
    for item in history:
        # Score is now net productive minutes. 6 minutes = 1 point (1 hour = 10 points)
        change = item['score'] / 6.0
        current_price += change
        if current_price < 0:
            current_price = 0
        item['price'] = current_price
        
    try:
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=4)
    except Exception:
        pass
        
    return history