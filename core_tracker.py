import subprocess
import time
import urllib.request
import urllib.parse
import json
import logging
from config import IDLE_THRESHOLD_SECS, log

try:
    from pynput import mouse, keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    PYNPUT_AVAILABLE = False


def get_active_window_title():
    # 1. Try Wayland: GNOME Shell Extension via gdbus (zero Python deps)
    try:
        result = subprocess.check_output(
            ['gdbus', 'call', '--session',
             '--dest', 'org.gnome.Shell',
             '--object-path', '/org/gnome/Shell/Extensions/ActiveWindow',
             '--method', 'org.gnome.Shell.Extensions.ActiveWindow.GetTitle'],
            stderr=subprocess.DEVNULL, timeout=2
        ).decode('utf-8').strip()
        # gdbus returns: ('Window Title',)
        if result.startswith("('") and result.endswith("',)"):
            title = result[2:-3]  # Strip ('...',)
            if title:
                return title.lower()
    except Exception:
        pass

    # 2. Fallback to X11 (xdotool) — works on Xorg sessions
    try:
        window_id = subprocess.check_output(['xdotool', 'getwindowfocus'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        window_name = subprocess.check_output(['xdotool', 'getwindowname', window_id], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        return window_name.lower()
    except Exception:
        return None


# ==========================================
# IDLE TRACKER SETUP
# ==========================================
last_input_time = time.time()

def on_input(*args, **kwargs):
    global last_input_time
    last_input_time = time.time()

if PYNPUT_AVAILABLE:
    try:
        mouse_listener = mouse.Listener(on_move=on_input, on_click=on_input, on_scroll=on_input)
        keyboard_listener = keyboard.Listener(on_press=on_input)
        # Daemon threads will exit when the main program exits
        mouse_listener.daemon = True
        keyboard_listener.daemon = True
        mouse_listener.start()
        keyboard_listener.start()
        log.info("Idle tracker started successfully.")
    except Exception as e:
        log.error(f"Failed to start pynput listeners: {e}")
        PYNPUT_AVAILABLE = False


def extract_domain_from_title(window_title):
    time.sleep(1) # Give ActivityWatch a second to sync the new window
    try:
        req = urllib.request.Request("http://localhost:5600/api/0/buckets")
        with urllib.request.urlopen(req, timeout=1) as response:
            buckets = json.loads(response.read().decode())
            
        web_buckets = [b for b in buckets if b.startswith("aw-watcher-web")]
        for bucket in web_buckets:
            req = urllib.request.Request(f"http://localhost:5600/api/0/buckets/{bucket}/events?limit=1")
            with urllib.request.urlopen(req, timeout=1) as response:
                events = json.loads(response.read().decode())
                if events:
                    event = events[0]
                    aw_title = event.get('data', {}).get('title', '')
                    
                    aw_lower = aw_title.lower()
                    win_lower = window_title.lower()
                    aw_words = set(aw_lower.split())
                    win_words = set(win_lower.split())
                    common_words = aw_words.intersection(win_words)
                    
                    if len(common_words) >= 2 or aw_title in window_title or window_title[:-15] in aw_title:
                        url = event['data'].get('url', '')
                        if url:
                            domain = urllib.parse.urlparse(url).netloc
                            if domain.startswith("www."):
                                domain = domain[4:]
                            if domain:
                                return domain
    except Exception:
        pass

    # Fallback to legacy string matching
    title_lower = window_title.lower()
    if 'crunchyroll' in title_lower: return 'crunchyroll.com'
    if '9anime' in title_lower or 'aniwatch' in title_lower: return 'aniwatch.to'
    if 'zoro' in title_lower: return 'zoro.to'
    if 'pornhub' in title_lower: return 'pornhub.com'
    if 'xvideos' in title_lower: return 'xvideos.com'
    if 'xhamster' in title_lower: return 'xhamster.com'
    if 'brazzers' in title_lower: return 'brazzers.com'
    if 'anikoto' in title_lower: return 'anikototv.to'
    
    words = title_lower.split()
    for w in words:
        if '.' in w and len(w) > 4:
            return w
    return None


def simplify_title(title):
    import re
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