import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from monitor import send_weekly_summary
from whatsapp import WhatsApp
from instagram import Instagram

print("[*] Initializing manual Weekly Audit trigger...")
wa = None
try:
    wa = WhatsApp()
except Exception as e:
    print(f"[-] WA init failed: {e}")

ig = None
# Not initializing IG here unless needed for speed

print("[*] Triggering send_weekly_summary()...")
send_weekly_summary(wa, ig)
