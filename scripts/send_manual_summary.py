import sys
import os
import datetime
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from monitor import send_daily_summary, load_stats
from whatsapp import WhatsApp
from instagram import Instagram

print("[*] Initializing manual trigger...")
wa = WhatsApp()
try:
    ig = Instagram()
except Exception:
    ig = None

time_spent, alert_level, saved_date = load_stats()
print("[*] Loaded stats. Triggering send_daily_summary()...")

send_daily_summary(time_spent, wa, ig)
print("[+] Done!")
