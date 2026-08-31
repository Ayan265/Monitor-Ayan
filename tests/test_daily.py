import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from monitor import send_daily_summary
from whatsapp import WhatsApp

def test():
    print("[*] Initializing WhatsApp...")
    wa = WhatsApp()
    
    # We pass an empty dict for time_spent, the AI or fallback will calculate it.
    time_spent = {}
    
    print("[*] Triggering send_daily_summary for 2026-07-17...")
    send_daily_summary(time_spent, wa_client=wa, ig_client=None, target_date_str="2026-07-17")
    print("[*] Done!")

if __name__ == "__main__":
    test()
