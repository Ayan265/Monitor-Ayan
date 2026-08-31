import time
import subprocess
import datetime
import os
import json
import logging
from config import log
from core_tracker import get_active_window_title, extract_domain_from_title
from alerts import send_alert


def trigger_nuclear_option(window_title, wa_client, ig_client):
    print("\n[!!!] TRIGGERING NUCLEAR OPTION [!!!]")
    log.error("NUCLEAR OPTION TRIGGERED!")
    
    # 0. Take screenshot BEFORE closing browsers
    screenshot_path = f"/tmp/accountability_alert_nuke_{int(time.time())}.png"
    try:
        subprocess.run("xdotool key Escape Escape Escape", shell=True)
        time.sleep(0.3)
        subprocess.run(f"import -window root {screenshot_path}", shell=True, check=True)
        subprocess.run("xdotool key Escape", shell=True)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", f"file://{screenshot_path}"])
    except Exception as e:
        print(f"[-] Failed to take screenshot for nuke: {e}")
        screenshot_path = None
    
    # 1. Extract Domain
    domain = extract_domain_from_title(window_title)
    
    # 2. Block Domain
    if domain:
        print(f"[*] Blocking domain: {domain}")
        subprocess.run(["sudo", "/home/linuxayan/Desktop/Monitor_ayan/scripts/blocker.sh", "add", domain])
        
        # Log to blocklist.json
        blocklist_path = "/home/linuxayan/Desktop/Monitor_ayan/data/blocklist.json"
        try:
            with open(blocklist_path, 'r') as f:
                blocklist = json.load(f)
        except:
            blocklist = {}
        blocklist[domain] = time.time()
        
        os.makedirs(os.path.dirname(blocklist_path), exist_ok=True)
        with open(blocklist_path, 'w') as f:
            json.dump(blocklist, f)
            
    # 3. Social Annihilation
    domain_str = f"'{domain}'" if domain else "The active domain"
    msg = f"🚨 [NUCLEAR BREACH] Ayan was just caught engaging in severe bad habits ('{window_title}').\n\nCONSEQUENCES TRIGGERED:\n1. {domain_str} blocked for 48 hours.\n2. Browsers force-closed."
    send_alert(msg, wa_client, ig_client, take_screenshot=False, delete_locally=True, custom_image_path=screenshot_path)
    
    # 4. Guillotine (Graceful Tab Close)
    try:
        print("[*] Gracefully closing the bad habit tab (Ctrl+W)...")
        # Double check if they alt-tabbed away during the 0.5s it took to block the domain
        current_now = get_active_window_title()
        if current_now == window_title:
            subprocess.run(["xdotool", "key", "ctrl+w"])
        else:
            # They switched windows! Find the exact bad window, bring it back, and kill the tab.
            search_proc = subprocess.run(['xdotool', 'search', '--name', window_title], capture_output=True, text=True)
            wids = search_proc.stdout.strip().split('\n')
            if wids and wids[0]:
                wid = wids[0]
                subprocess.run(['xdotool', 'windowactivate', '--sync', wid])
                time.sleep(0.1)
                subprocess.run(["xdotool", "key", "ctrl+w"])
    except Exception as e:
        print(f"[-] Failed to gracefully close tab: {e}")
    
    # 6. Ransomware (Respawning) - Removed