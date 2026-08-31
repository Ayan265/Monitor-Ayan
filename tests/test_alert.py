import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from whatsapp import WhatsApp
from instagram import Instagram
from monitor import send_alert
import time
import os

wa = WhatsApp()
ig = Instagram()

wa.start_client()
print("Waiting 5 seconds for WA to init...")
time.sleep(5)

print("Triggering test alert...")
send_alert("🚨 [TEST ALERT] Verifying image delivery of the active window.", wa, ig, take_screenshot=True)
