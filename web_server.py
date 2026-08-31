import time
import subprocess
import datetime
import os
import sys
import signal
import logging
from flask import Flask, request, jsonify

# Mobile webhook globals
flask_app = Flask(__name__)

wa_global = None
ig_global = None

last_alert_time = 0
last_heartbeat_time = time.time()
heartbeat_failed = False


def get_logical_today():
    """Returns today's date, but shifts to tomorrow if the time is 22:00 or later.
       This forces the 'daily reset' to trigger at 10 PM instead of midnight."""
    now = datetime.datetime.now()
    if now.hour >= 22:
        return (now + datetime.timedelta(days=1)).date()
    return now.date()


def run_flask():
    import logging
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    flask_app.run(host='0.0.0.0', port=5000, use_reloader=False)


def send_mobile_alert(keyword, app_name):
    global wa_global, ig_global
    print(f"\n[!!!] MACRODROID TRIGGERED! Caught keyword: {keyword} in app: {app_name}")
    msg = f"🚨 DISGUSTING BEHAVIOR DETECTED ON MOBILE: Ayan is currently looking at '{keyword}' inside the '{app_name}' app instead of working on his goals. He was caught accessing it on his Android phone. Please call him immediately and hold him accountable for his lack of discipline. Do not let him make excuses."
    from alerts import send_alert
    send_alert(msg, wa_global, ig_global)


@flask_app.route('/alert', methods=['POST'])
def handle_alert():
    global last_alert_time
    data = request.json or {}
    keyword = data.get('keyword', 'adult content')
    app_name = data.get('app', 'unknown')
    if time.time() - last_alert_time < 10:
        return jsonify({"status": "ignored", "reason": "rate limit"}), 429
    last_alert_time = time.time()
    send_mobile_alert(keyword, app_name)
    return jsonify({"status": "success"}), 200


@flask_app.route('/heartbeat', methods=['GET'])
def handle_heartbeat():        
    global last_heartbeat_time, heartbeat_failed
    last_heartbeat_time = time.time()
    if heartbeat_failed:
        heartbeat_failed = False
        print("[*] Heartbeat restored.")
    return jsonify({"status": "alive"}), 200


def is_system_shutting_down():
    try:
        res = subprocess.run(["systemctl", "is-system-running"], capture_output=True, text=True)
        if "stopping" in res.stdout:
            return True
        res_user = subprocess.run(["systemctl", "--user", "is-system-running"], capture_output=True, text=True)
        if "stopping" in res_user.stdout:
            return True
        jobs = subprocess.run(["systemctl", "list-jobs"], capture_output=True, text=True)
        if "poweroff.target" in jobs.stdout or "reboot.target" in jobs.stdout or "halt.target" in jobs.stdout or "logout.target" in jobs.stdout:
            return True
    except Exception:
        pass
    return False

def shutdown_trap(signum, frame):
    global wa_global, ig_global
    if is_system_shutting_down():
        print("\n[*] System is shutting down or logging out. Exiting peacefully.")
        sys.exit(0)
        
    msg = "🚨 [COWARDICE] Ayan just killed his accountability monitor! He's trying to hide his screen and bypass tracking. Confront him immediately!"
    print("\n[!] SHUTDOWN TRAP TRIGGERED! Sending dying breath alert...")
    from alerts import send_alert
    send_alert(msg, wa_global, ig_global, block=True)
    sys.exit(0)


signal.signal(signal.SIGTERM, shutdown_trap)