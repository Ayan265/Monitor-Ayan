import time
import subprocess
import datetime
import os
import json
import logging
from config import log
from core_tracker import get_active_window_title, extract_domain_from_title
from alerts import send_alert

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def trigger_nuclear_option(window_title, wa_client, ig_client):
    print("\n[!!!] TRIGGERING NUCLEAR OPTION [!!!]")
    log.error("NUCLEAR OPTION TRIGGERED!")
    
    # 0. Take screenshot BEFORE closing browsers (Wayland-safe)
    screenshot_path = f"/tmp/accountability_alert_nuke_{int(time.time())}.png"
    try:
        ss_script = os.path.join(SCRIPT_DIR, "scripts", "wayland_screenshot.py")
        result = subprocess.run(
            ["/usr/bin/python3", ss_script, screenshot_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and os.path.exists(screenshot_path):
            # Set as wallpaper of shame
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri", f"file://{screenshot_path}"])
            subprocess.run(["gsettings", "set", "org.gnome.desktop.background", "picture-uri-dark", f"file://{screenshot_path}"])
        else:
            print(f"[-] Failed to take screenshot for nuke: {result.stderr.strip()}")
            screenshot_path = None
    except Exception as e:
        print(f"[-] Failed to take screenshot for nuke: {e}")
        screenshot_path = None
    
    # 1. Extract Domain
    domain = extract_domain_from_title(window_title)
    
    # 2. Block Domain
    if domain:
        print(f"[*] Blocking domain: {domain}")
        blocker_script = os.path.join(SCRIPT_DIR, "scripts", "blocker.sh")
        subprocess.run(["sudo", blocker_script, "add", domain])
        
        # Log to blocklist.json
        blocklist_path = os.path.join(SCRIPT_DIR, "data", "blocklist.json")
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
    
    # 4. Guillotine (Close the tab via wmctrl or xdg — best effort on Wayland)
    try:
        print("[*] Attempting to close the bad habit window...")
        # On Wayland, xdotool can't target windows. Use wmctrl or pkill browser as fallback.
        subprocess.run(["pkill", "-f", "firefox"], timeout=5)
        subprocess.run(["pkill", "-f", "chrome"], timeout=5)
        subprocess.run(["pkill", "-f", "chromium"], timeout=5)
    except Exception as e:
        print(f"[-] Failed to close browser: {e}")
    
    # 6. Ransomware (Respawning) - Removed