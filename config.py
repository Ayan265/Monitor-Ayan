"""
config.py — All settings and constants for the Accountability Monitor.

Change your rules, alert targets, and file paths HERE instead of
digging through the 1400+ line monitor.py.
"""

import os
import logging
import json

# ==========================================
# SCRIPT PATHS
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "data", "activity_history.csv")
MONITOR_LOG = os.path.join(SCRIPT_DIR, "logs", "monitor.log")
STATS_FILE = os.path.join(SCRIPT_DIR, "data", "daily_stats.json")
STREAK_FILE = os.path.join(SCRIPT_DIR, "data", "streak.json")
QUEUE_FILE = os.path.join(SCRIPT_DIR, "data", "failed_messages.json")

# ==========================================
# LOGGING
# ==========================================
logging.basicConfig(
    filename=MONITOR_LOG,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger("monitor")

# ==========================================
# RULES & CATEGORY DEFINITIONS
# ==========================================
# Each category has:
#   - keywords: what window titles to match (lowercase)
#   - escalations: list of (seconds_threshold, alert_message) tuples
#
# Bad habits trigger alerts to your friend.
# Good habits (coding, research) send celebration messages at milestones.

# Load generic rules by default
RULES = {
    "bad_habit": {
        "keywords": [
            "porn", "pornhub", "xvideos", "xhamster", "spankbang", "xnxx", 
            "redtube", "brazzers", "hentai", "jav", "rule34", "chaturbate"
        ],
        "escalations": [
            (60, "🚨 [ALERT] The user is watching restricted content right now instead of working. Call them and make them stop."),
            (300, "🚨 [ALERT] 5 FULL MINUTES of restricted content. The user is completely lacking discipline and ignoring warnings. CALL THEM IMMEDIATELY.")
        ]
    },
    "anime_manga": {
        "keywords": ["anime", "crunchyroll", "aniwatch", "9anime", "zoro", "manga", "all manga", "mangadex", "episode", "season", "subbed", "dubbed"],
        "escalations": [
            (300, "🚨 [ALERT] The user is wasting time on Anime/Manga ('{window_title}'). They've been distracted for 5+ mins. Tell them to get to work."),
            (900, "🚨 [ALERT] 15 Mins wasted on '{window_title}'. They are losing discipline. Call them and force them to close it."),
            (1800, "🚨 [ALERT] 30 Mins wasted on Anime! They have completely given up on their goals today. Hold them accountable.")
        ]
    },
    "coding": {
        "keywords": ["vs code", "antigravity", "terminal"],
        "escalations": [
            (14400, "🌟 [DISCIPLINE] The user just hit 4 hours of coding. Hard work pays off!")
        ]
    },
    "research": {
        "keywords": ["screener", "bseindia", "equity", "finance"],
        "escalations": [
            (14400, "📈 [DISCIPLINE] The user just spent 4 hours doing equity research. Good focus!")
        ]
    }
}

# Generic Targets
SUMMARY_WHATSAPP_TARGETS = ["YOUR_SUMMARY_GROUP"]
ALERT_WHATSAPP_TARGETS = ["YOUR_ALERT_GROUP"]
ALERT_IG_USERNAMES = []

# Generic Messages
MESSAGES = {
    "PROTOCOL_FAILED": "[PROTOCOL FAILED] The user failed to complete the required amount of productive work. Protocol triggered.",
    "PROMPT_TIMEOUT": "🚨 [PROMPT TIMEOUT] The user ignored the 'Accountability Check' prompt for {allowed_time} seconds! They are slacking."
}
AI_ROAST_OVERRIDE_TARGET = None
AI_ROAST_OVERRIDE = None

# ==========================================
# TIMING CONSTANTS
# ==========================================
IDLE_THRESHOLD_SECS = 180    # 3 minutes — after this, user is considered idle
WA_KEEPALIVE_SECS = 300      # Keep WhatsApp alive for 5 mins after bad_habit detection
IG_KEEPALIVE_SECS = 300      # Keep Instagram alive for 5 mins after bad_habit detection

# Default API Key
GEMINI_API_KEY = "YOUR_API_KEY_HERE"

# ==========================================
# LOAD PRIVATE SECRETS
# ==========================================
SECRETS_FILE = os.path.join(SCRIPT_DIR, "private", "secrets.json")
if os.path.exists(SECRETS_FILE):
    try:
        with open(SECRETS_FILE, "r") as f:
            _secrets = json.load(f)
            GEMINI_API_KEY = _secrets.get("GEMINI_API_KEY", GEMINI_API_KEY)
            SUMMARY_WHATSAPP_TARGETS = _secrets.get("SUMMARY_WHATSAPP_TARGETS", SUMMARY_WHATSAPP_TARGETS)
            ALERT_WHATSAPP_TARGETS = _secrets.get("ALERT_WHATSAPP_TARGETS", ALERT_WHATSAPP_TARGETS)
            ALERT_IG_USERNAMES = _secrets.get("ALERT_IG_USERNAMES", ALERT_IG_USERNAMES)
            
            if "MESSAGES" in _secrets:
                MESSAGES.update(_secrets["MESSAGES"])
                AI_ROAST_OVERRIDE_TARGET = _secrets["MESSAGES"].get("AI_ROAST_OVERRIDE_TARGET")
                AI_ROAST_OVERRIDE = _secrets["MESSAGES"].get("AI_ROAST_OVERRIDE")
                
            if "RULES" in _secrets:
                # Convert list escalations back to tuples
                _rules = _secrets["RULES"]
                for cat in _rules:
                    _rules[cat]["escalations"] = [tuple(esc) for esc in _rules[cat]["escalations"]]
                RULES = _rules
                
    except Exception as e:
        log.error(f"Failed to load private/secrets.json: {e}")

# ==========================================

