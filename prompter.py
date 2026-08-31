import time
import subprocess
import csv
import datetime
import threading
import json
import os
import re
from config import (
    LOG_FILE, RULES,
    SUMMARY_WHATSAPP_TARGETS, ALERT_WHATSAPP_TARGETS, ALERT_IG_USERNAMES,
    log
)

# Global clients (set by main.py)
wa_global = None
ig_global = None


def activity_prompter_thread():
    """
    Every 20 minutes, asks the user what they did via Zenity.
    If ignored or canceled, sends a harsh accountability alert.
    """
    global wa_global, ig_global
    
    interval_seconds = 1200 # 20 minutes
    timeout_seconds = 180   # 3 minutes
    wasted_blocks = 0
    
    last_prompt_time = datetime.datetime.now()

    def get_recent_top_apps(since_time, top_n=None):
        try:
            if not os.path.exists(LOG_FILE):
                return []
                
            cutoff_str = since_time.strftime("%Y-%m-%d %H:%M:%S")
            app_times = {}
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None) # skip header
                for row in reader:
                    if len(row) >= 3:
                        try:
                            duration = int(row[-1])
                            ts = row[0]
                            title = row[1] if len(row) == 3 else " ".join(row[1:-1])
                        except (ValueError, IndexError):
                            continue
                        if ts >= cutoff_str:
                            if not title or "desktop icons" in title.lower() or "gnome-shell" in title.lower():
                                continue
                            clean_title = title.strip()
                            for suffix in [" — mozilla firefox", " - mozilla firefox", " - google chrome", " - brave", " - text editor"]:
                                if clean_title.lower().endswith(suffix):
                                    clean_title = clean_title[:-len(suffix)]
                            clean_title = re.sub(r'^\(\d+\)\s*', '', clean_title.strip())
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
                            app_times[short_title] = app_times.get(short_title, 0) + duration
            sorted_apps = sorted(app_times.items(), key=lambda x: x[1], reverse=True)
            return sorted_apps if top_n is None else sorted_apps[:top_n]
        except Exception as e:
            print(f"Error getting recent apps: {e}")
            return []

    while True:
        time.sleep(interval_seconds)
        try:
            # Capture the current time as the start of the next interval BEFORE prompt
            next_prompt_time = datetime.datetime.now()
            
            recent_apps = get_recent_top_apps(last_prompt_time, top_n=None)
            recent_text = "\n\nTime Spend:\n"
            if recent_apps:
                total_time = sum(secs for _, secs in recent_apps)
                if total_time > 0:
                    display_apps = []
                    others_pct = 0
                    
                    for app, secs in recent_apps:
                        pct = (secs / total_time) * 100
                        if pct >= 5:
                            display_apps.append((app, pct))
                        else:
                            others_pct += pct
                            
                    for i, (app, pct) in enumerate(display_apps, 1):
                        recent_text += f"{i}. {app} {int(round(pct))}%\n"
                        
                    if others_pct > 0:
                        recent_text += f"{len(display_apps) + 1}. Others {int(round(others_pct))}%\n"
                else:
                    recent_text += "No active apps tracked.\n"
            else:
                recent_text += "No active apps tracked.\n"
                
            # --- Check Productivity for Mandatory Protocol ---
            productive_secs = 0
            total_secs = 0
            if recent_apps:
                for app, secs in recent_apps:
                    total_secs += secs
                    app_lower = app.lower()
                    is_prod = False
                    for cat in ["coding", "research"]:
                        for kw in RULES[cat]["keywords"]:
                            if kw in app_lower:
                                is_prod = True
                                break
                        if is_prod: break
                    if is_prod:
                        productive_secs += secs
                        
                if total_secs > 0:
                    productive_pct = (productive_secs / total_secs) * 100
                    if productive_pct < 20: # Over 80% wasted
                        wasted_blocks += 1
                    else:
                        wasted_blocks = 0
                else:
                    wasted_blocks = 0
                    
                if wasted_blocks >= 2:
                    from mandatory_work import start_mandatory_protocol
                    start_mandatory_protocol(wa_global, ig_global)
                    wasted_blocks = 0
            else:
                wasted_blocks = 0
                
            prompt_text = "What did you do in the last 20 minutes?" + recent_text

            print("[*] Launching 20-minute accountability prompt...")
            
            # Start background music
            player_proc = None
            try:
                player_proc = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", "-loop", "0", "/home/ayan/dev/Monitor_ayan/music/A New Big Bang Ben 10.mp3"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                log.error(f"Failed to play music: {e}")

            # Keep window on top
            keep_focus = True
            def force_focus():
                while keep_focus:
                    try:
                        subprocess.run(["xdotool", "search", "--name", "Accountability Check", "windowactivate"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                    except:
                        pass
                    time.sleep(1)
            threading.Thread(target=force_focus, daemon=True).start()

            # Run zenity
            result = subprocess.run(
                [
                    "zenity", 
                    "--entry", 
                    "--title=Accountability Check", 
                    "--text=" + prompt_text, 
                    f"--timeout={timeout_seconds}"
                ],
                capture_output=True,
                text=True
            )
            
            keep_focus = False # Stop focus thread
            if player_proc:
                try:
                    player_proc.terminate()
                except:
                    pass
            
            # Update last_prompt_time for next iteration
            last_prompt_time = next_prompt_time

            if result.returncode == 0 and result.stdout.strip():
                user_response = result.stdout.strip()
                msg = f"Ayan Last 20 mins: {user_response}\n{recent_text.strip()}"
                print(f"[+] User responded: {user_response}")
                from alerts import send_alert
                send_alert(msg, wa_global, ig_global, take_screenshot=False, delete_locally=False, custom_targets=config.ALERT_WHATSAPP_TARGETS)
            else:
                msg = config.MESSAGES.get("PROMPT_TIMEOUT", f"🚨 [PROMPT TIMEOUT] The user ignored the '{prompt_msg}' prompt for {{allowed_time}} seconds! They are slacking.")
                msg = msg.replace("{allowed_time}", str(allowed_time))
                # Take screenshot for timeout failure
                from alerts import send_alert
                send_alert(msg, wa_global, ig_global, take_screenshot=True, delete_locally=False, custom_targets=config.ALERT_WHATSAPP_TARGETS)
                
        except Exception as e:
            log.error(f"Activity prompter thread error: {e}")
            print(f"[-] Activity prompter thread error: {e}")