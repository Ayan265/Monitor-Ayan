import time
import subprocess
import datetime
import os
import sys
import threading
import csv

# --- Prevent Errno 5 (Input/output error) when terminal is closed ---
class SafeStream:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        try:
            self.stream.write(data)
            self.stream.flush()
        except Exception:
            pass
    def flush(self):
        try:
            self.stream.flush()
        except Exception:
            pass
sys.stdout = SafeStream(sys.stdout)
sys.stderr = SafeStream(sys.stderr)
# --------------------------------------------------------------------

from config import (
    RULES, LOG_FILE, STATS_FILE, STREAK_FILE, IDLE_THRESHOLD_SECS,
    SUMMARY_WHATSAPP_TARGETS, ALERT_WHATSAPP_TARGETS, ALERT_IG_USERNAMES,
    log
)

# Import all modules
from web_server import run_flask, get_logical_today, wa_global, ig_global
from core_tracker import get_active_window_title
from data_manager import (
    log_to_csv, load_stats, save_stats, cleanup_old_data, 
    get_streak, update_streak, get_weekly_time_sinks
)
from alerts import send_alert, retry_failed_messages, queue_failed_message
from ai_reports import send_daily_summary, send_weekly_summary
from punishments import trigger_nuclear_option
from prompter import activity_prompter_thread, wa_global as prompter_wa_global, ig_global as prompter_ig_global


def _stop_syncthing():
    """Kill Syncthing process to free memory. It auto-starts via GNOME on next boot."""
    try:
        subprocess.run(['pkill', '-f', 'syncthing'], timeout=5)
        print("[*] Syncthing stopped to save memory.")
        log.info("Syncthing killed after mobile data sync.")
    except Exception:
        pass


def sync_mobile_data(max_wait=300, poll_interval=10):
    """Wait for Syncthing to deliver a fresh mobile Activity Watch file,
    then kill Syncthing to free memory (no more work left for it).
    
    Syncthing is already running (GNOME autostart). This function waits
    for the mobile file's mtime to change, meaning the phone has sent a new
    version. Used by the Recovery Protocol before sending missed summaries.
    Returns True if the file was updated, False if timed out.
    """
    mobile_file = "/home/ayan/A/activity watch"
    old_mtime = os.path.getmtime(mobile_file) if os.path.exists(mobile_file) else 0
    old_date = datetime.datetime.fromtimestamp(old_mtime).strftime('%Y-%m-%d %H:%M') if old_mtime else "never"

    print(f"[*] Waiting for Syncthing to sync mobile data (file last modified: {old_date})...")
    log.info(f"Waiting for mobile AW file sync. Current mtime: {old_date}")
    
    try:
        subprocess.Popen(['syncthing', '-no-browser'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("[*] Syncthing started on-demand for mobile data sync.")
    except Exception as e:
        log.error(f"Failed to start syncthing: {e}")

    # Wait for file to update
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(poll_interval)
        try:
            if os.path.exists(mobile_file):
                new_mtime = os.path.getmtime(mobile_file)
                if new_mtime > old_mtime:
                    elapsed = int(time.time() - start)
                    new_date = datetime.datetime.fromtimestamp(new_mtime).strftime('%Y-%m-%d %H:%M')
                    print(f"[+] Mobile Activity Watch file synced! (took {elapsed}s, new mtime: {new_date})")
                    log.info(f"Syncthing delivered fresh mobile data in {elapsed}s.")
                    _stop_syncthing()
                    return True
        except OSError:
            pass

    print(f"[-] Syncthing sync timed out after {max_wait}s. Proceeding with existing data.")
    log.warning(f"Syncthing sync timed out after {max_wait}s.")
    _stop_syncthing()
    return False


if __name__ == "__main__":
    print("=== Digital Accountability Monitor ===")
    log.info("Monitor starting up...")
    
    # 1. Boot up the messengers (lazy — no actual connection until needed)
    print("[*] Initializing messenger clients...")
    wa = None
    ig = None
    try:
        from whatsapp import WhatsApp
        wa = WhatsApp()
        print("[+] WhatsApp client wrapper ready.")
    except Exception as e:
        log.error(f"WhatsApp init failed: {e}")
        print(f"[-] WhatsApp init failed (will continue without it): {e}")

    # try:
    #     from instagram import Instagram
    #     ig = Instagram()
    #     print("[+] Instagram client wrapper ready.")
    # except Exception as e:
    #     log.error(f"Instagram init failed: {e}")
    #     print(f"[-] Instagram init failed (will continue without it): {e}")

    # Set global clients for web server and prompter
    import web_server
    import prompter
    web_server.wa_global = wa
    web_server.ig_global = ig
    prompter.wa_global = wa
    prompter.ig_global = ig

    print("[*] Starting Mobile Webhook Thread...")
    threading.Thread(target=run_flask, daemon=True).start()

    print("[*] Starting 20-Minute Accountability Prompter Thread...")
    threading.Thread(target=activity_prompter_thread, daemon=True).start()

    print("[+] Monitoring started...\n")
    log.info("Monitoring started.")
    
    # Create CSV header if it doesn't exist
    try:
        with open(LOG_FILE, 'x', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow(["Timestamp", "Window Title", "Duration (Seconds)"])
    except FileExistsError:
        pass
    
    last_title = ""
    last_nuked_title = ""
    window_start_time = time.time()
    
    # Dynamically setup tracking counters based on RULES
    # Dynamically setup tracking counters based on RULES (load from persistence if available)
    time_spent, alert_level, saved_date = load_stats()
    current_day = get_logical_today()
    current_day_str = str(current_day)
    
    # --- RECOVERY PROTOCOL ---
    if saved_date and saved_date != current_day_str:
        print(f"[*] Recovery Send: Sending missed summary for {saved_date}")
        log.info(f"Recovery Send for {saved_date}")

        # Pull fresh mobile data from phone via Syncthing before sending summary
        synced = sync_mobile_data(max_wait=300, poll_interval=10)
        if synced:
            log.info("Syncthing delivered fresh mobile data for recovery summary.")
        else:
            log.warning("Syncthing sync timed out. Proceeding with stale mobile data.")

        try:
            send_daily_summary(time_spent, wa, ig, target_date_str=saved_date)
        except Exception as e:
            log.error(f"Failed to send daily summary during recovery: {e}")
            print(f"[-] Failed to send daily summary during recovery: {e}")
        
        # Trigger weekly summary if the recovered day was Sunday (weekday 6)
        try:
            saved_date_obj = datetime.datetime.strptime(saved_date, "%Y-%m-%d").date()
            if saved_date_obj.weekday() == 6:
                print("[*] Recovery Weekly Summary: Sunday midnight missed during sleep/suspend. Triggering Weekly Macro Audit.")
                log.info("Triggering Weekly Macro Audit during recovery.")
                try:
                    send_weekly_summary(wa, ig)
                except Exception as e:
                    log.error(f"Failed to send weekly summary during recovery: {e}")
        except Exception as e:
            log.error(f"Failed to parse or trigger weekly summary in recovery: {e}")
        
        # Reset counters for today
        time_spent = {category: 0 for category in RULES.keys()}
        alert_level = {category: 0 for category in RULES.keys()}
        save_stats(time_spent, alert_level)

    wa_booted = False        # Whether WA client has been JIT started this session
    wa_boot_time = 0         # When WA was last started (to auto-stop after cooldown)
    WA_KEEPALIVE_SECS = 300  # Keep WA alive for 5 minutes after last bad_habit detection

    ig_booted = False        # Whether IG client has been JIT started this session
    ig_boot_time = 0         # When IG was last started
    IG_KEEPALIVE_SECS = 300  # Keep IG alive for 5 minutes after last bad_habit detection

    last_retry_time = time.time()
    last_loop_time = time.time()

    try:
        while True:
            try:
                if time.time() - last_retry_time > 300:
                    retry_failed_messages(wa, ig)
                    
                    # Periodic Maintenance (The Unblocker)
                    blocklist_path = "/home/ayan/dev/Monitor_ayan/data/blocklist.json"
                    if os.path.exists(blocklist_path):
                        try:
                            with open(blocklist_path, 'r') as f:
                                blocklist = json.load(f)
                            new_blocklist = {}
                            now = time.time()
                            for dom, timestamp in blocklist.items():
                                if now - timestamp > 172800: # 48 hours
                                    print(f"[*] 48 hours passed. Unblocking {dom}")
                                    subprocess.run(["sudo", "/home/ayan/dev/Monitor_ayan/scripts/blocker.sh", "remove", dom])
                                else:
                                    new_blocklist[dom] = timestamp
                            with open(blocklist_path, 'w') as f:
                                json.dump(new_blocklist, f)
                        except Exception as e:
                            log.error(f"Failed to process blocklist: {e}")

                    # --- WA HEALTH WATCHDOG ---
                    try:
                        import requests as _req
                        health = _req.get("http://localhost:3001/health", timeout=3).json()
                        if health.get("needsQRScan"):
                            log.warning("[WATCHDOG] WA needs QR re-scan. Desktop notification sent.")
                        elif not health.get("ready") and not health.get("alive"):
                            log.warning("[WATCHDOG] WA backend dead. Triggering force_restart...")
                            wa.force_restart()
                    except _req.exceptions.ConnectionError:
                        log.warning("[WATCHDOG] WA backend unreachable. Triggering force_restart...")
                        wa.force_restart()
                    except Exception as e:
                        log.error(f"[WATCHDOG] Health check error: {e}")
                    # --- END WA WATCHDOG ---
                            
                    last_retry_time = time.time()
                    
                # Heartbeat check disabled to prevent false positives when Android puts the phone to sleep
                # if not heartbeat_failed and (time.time() - last_heartbeat_time > 900):
                #     heartbeat_failed = True
                #     hb_msg = "🚨 [TAMPERED] Ayan's phone stopped sending security heartbeats. He likely disabled his monitoring app to hide. Demand an explanation!"
                #     print("\n[!!!] HEARTBEAT FAILED: Sending tamper alert!")
                #     send_alert(hb_msg, wa, ig)
                    
                # Check for midnight reset or missed summary during sleep
                now_time = time.time()
                if now_time - last_loop_time > 600:
                    log.info(f"System woke up from sleep/suspend. Asleep for {int(now_time - last_loop_time)} seconds.")
                    print(f"[*] System woke up from sleep. (Asleep for {int(now_time - last_loop_time)}s)")
                
                last_loop_time = now_time

                if get_logical_today() != current_day:
                    print(f"[*] Midnight reached! (Logical today: {get_logical_today()}, Last day: {current_day})")
                    log.info("Midnight reset of counters. Sending summary.")
                    try:
                        if str(current_day) == "2026-08-02":
                            print("[*] Skipping daily summary for today as requested. Everything got normal.")
                        else:
                            send_daily_summary(time_spent, wa, ig, target_date_str=str(current_day))
                    except Exception as e:
                        log.error(f"Failed to send daily summary: {e}")
                        print(f"[-] Failed to send daily summary: {e}")
                    
                    # --- NEW: Maintenance and Weekly Triggers ---
                    cleanup_old_data()
                    
                    if current_day.weekday() == 6:
                        print("[*] Sunday midnight reached! Triggering Weekly Macro Audit.")
                        try:
                            send_weekly_summary(wa, ig)
                        except Exception as e:
                            log.error(f"Failed to send weekly summary: {e}")
                    # --------------------------------------------
                    
                    time_spent = {category: 0 for category in RULES.keys()}
                    alert_level = {category: 0 for category in RULES.keys()}
                    save_stats(time_spent, alert_level)
                    current_day = get_logical_today()
                    wa_booted = False  # Summary stops the client

                current_title = get_active_window_title()
                
                is_bad_habit_active = False
                
                # --- CHECK CATEGORY DURATIONS ---
                if current_title:
                    # Did the user switch to a new window?
                    if current_title != last_title:
                        if last_title:
                            duration = int(time.time() - window_start_time)
                            
                            # Only record it to the permanent history file if you stared at it for > 2 seconds
                            # (This prevents spamming the file when you quickly Alt-Tab between 10 windows)
                            if duration >= 2:
                                log_to_csv(last_title, duration)

                        print(f"[*] Now looking at: {current_title}")
                        last_title = current_title
                        window_start_time = time.time() # Reset the stopwatch for the new window

                    for category, rule in RULES.items():
                        for keyword in rule["keywords"]:
                            if keyword in current_title:
                                # Anti-Cheating Idle Tracker: Check if user is idle
                                from core_tracker import PYNPUT_AVAILABLE, last_input_time
                                is_idle = PYNPUT_AVAILABLE and (time.time() - last_input_time) > IDLE_THRESHOLD_SECS
                                
                                # Do not count idle time for positive habits (coding, research)
                                # But still increment bad_habit even if idle (could be watching video hands-free)
                                if is_idle and category in ["coding", "research"]:
                                    continue
                                
                                # Add 1 second to this category's cumulative total
                                time_spent[category] += 1
                                
                                # Persist to disk every 5 seconds to avoid data loss on crash
                                if time_spent[category] % 5 == 0:
                                    save_stats(time_spent, alert_level)
                                
                                # --- NO HARD BLOCK ---
                                # Hard block removed so user can reach the 60s snitch threshold.
                                
                                # --- JIT LOGIC: PRE-LOAD MESSENGERS (start once, keep alive) ---
                                if category == "bad_habit":
                                    is_bad_habit_active = True
                                    if wa:
                                        wa_boot_time = time.time()  # Reset cooldown timer
                                        if not wa_booted:
                                            try:
                                                print("[*] Bad habit detected. JIT Booting WhatsApp secretly...")
                                                wa.start_client()
                                                wa_booted = True
                                            except Exception as e:
                                                log.error(f"WA JIT start failed: {e}")
                                                print(f"[-] WA JIT start failed: {e}")
                                                
                                    if ig:
                                        ig_boot_time = time.time()
                                        if not ig_booted:
                                            try:
                                                print("[*] Bad habit detected. JIT Booting Instagram secretly...")
                                                ig.start_client()
                                                ig_booted = True
                                            except Exception as e:
                                                log.error(f"IG JIT start failed: {e}")
                                                print(f"[-] IG JIT start failed: {e}")
                                
                                # --- Final Warning System ---
                                if category == "bad_habit" and time_spent[category] == (RULES["bad_habit"]["escalations"][0][0] // 2):
                                    try:
                                        subprocess.run(['notify-send', '-u', 'critical', '🚨 ACCOUNTABILITY WARNING', 'Close this immediately or your friend will be notified!'])
                                    except Exception:
                                        pass

                                # --- CONTINUOUS BAD HABIT LOGIC (Every 1 minute) ---
                                if category == "bad_habit":
                                    if time_spent[category] >= 60 and time_spent[category] % 60 == 0:
                                        mins = time_spent[category] // 60
                                        alert_msg = f"🚨 [SHAME] Ayan has been watching PORN for {mins} straight minutes! He is STILL watching it right now. This is not a test. Call him and hold him accountable! No excuses."
                                        send_alert(alert_msg, wa, ig, take_screenshot=True)
                                        
                                        # Keep alert level updated for reference if needed
                                        alert_level[category] = mins
                                        save_stats(time_spent, alert_level)

                                    if time_spent[category] >= 120 and current_title != last_nuked_title:
                                        trigger_nuclear_option(current_title, wa, ig)
                                        last_nuked_title = current_title
                                # --- STANDARD ESCALATION LOGIC (For other categories) ---
                                else:
                                    current_level = alert_level.get(category, 0)
                                    escalations = rule.get("escalations", [])
                                    
                                    if current_level < len(escalations):
                                        next_threshold, message_template = escalations[current_level]
                                        if time_spent[category] >= next_threshold:
                                            if message_template == "NUCLEAR":
                                                trigger_nuclear_option(current_title, wa, ig)
                                            else:
                                                alert_msg = message_template.replace("{window_title}", current_title.title())
                                                take_ss = category in ["anime_manga"] # bad_habit is handled above
                                                send_alert(alert_msg, wa, ig, take_screenshot=take_ss)
                                                
                                            alert_level[category] = current_level + 1
                                            save_stats(time_spent, alert_level)
                                
                                break # We found a match, stop checking other keywords
                
                if not is_bad_habit_active:
                    last_nuked_title = ""

                # --- Auto-stop WA after cooldown (no more thrashing on every window switch) ---
                if wa_booted and wa and (time.time() - wa_boot_time > WA_KEEPALIVE_SECS):
                    try:
                        print("[*] WA cooldown expired. Stopping client to save memory.")
                        wa.stop_client()
                    except Exception as e:
                        log.error(f"WA stop_client failed: {e}")
                    wa_booted = False
                    
                # --- Auto-stop IG after cooldown ---
                if ig_booted and ig and (time.time() - ig_boot_time > IG_KEEPALIVE_SECS):
                    try:
                        print("[*] IG cooldown expired. Stopping client to save memory.")
                        ig.stop_client()
                    except Exception as e:
                        log.error(f"IG stop_client failed: {e}")
                    ig_booted = False

            except Exception as e:
                # SAFETY NET: A single iteration failure must NEVER kill the monitoring loop
                log.error(f"Loop iteration error (recovering): {e}")
                print(f"[-] Error in loop (recovering): {e}")

            time.sleep(1) # Run check once per second
            
    except KeyboardInterrupt:
        # Log the final window before exiting
        if last_title:
            log_to_csv(last_title, int(time.time() - window_start_time))
            
        print("\n\n[+] Monitor stopped. Here are your stats for this session:")
        for category, seconds in time_spent.items():
            print(f"    - {category.capitalize()}: {seconds // 60} minutes, {seconds % 60} seconds")
        print(f"\n[+] Full history saved to: {LOG_FILE}")
        log.info("Monitor stopped by user.")