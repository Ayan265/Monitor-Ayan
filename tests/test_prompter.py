import subprocess
import sys
import os
sys.path.append('/home/linuxayan/Desktop/Monitor_ayan')
from whatsapp import WhatsApp
from instagram import Instagram

print("[*] Initializing test prompt...")
try:
    wa_global = WhatsApp()
    wa_global.start_client()
except Exception:
    wa_global = None

ig_global = None

def send_alert(message, wa_client, ig_client, take_screenshot=False):
    print(f"\n[!!!] TRIGGERING ALERT: {message}")
    if wa_client:
        try:
            import time
            for _ in range(10):
                if wa_client.is_ready():
                    break
                time.sleep(1)
            wa_client.send_alert_msg("Monitor Ayan", message, None)
        except Exception as e:
            print(f"WhatsApp alert failed: {e}")

print("[*] Launching 20-minute accountability prompt (TEST MODE)...")
result = subprocess.run(
    [
        "zenity", 
        "--entry", 
        "--title=Accountability Check", 
        "--text=What did you do in the last 20 minutes? (TEST)", 
        "--timeout=30"
    ],
    capture_output=True,
    text=True
)

if result.returncode == 0 and result.stdout.strip():
    user_response = result.stdout.strip()
    msg = f"✅ [ACCOUNTABILITY UPDATE TEST] Ayan's update for the last 20 mins:\n\n\"{user_response}\""
    print(f"[+] User responded: {user_response}")
    send_alert(msg, wa_global, ig_global, take_screenshot=False)
else:
    print("[-] User ignored or canceled the accountability prompt!")
    msg = "🚨 [SILENCE DETECTED TEST] ayan dont doing something worthy saying that why i wont writing what ayan did last 15 min"
    send_alert(msg, wa_global, ig_global, take_screenshot=True)
