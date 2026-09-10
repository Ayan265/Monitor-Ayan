import time
import threading
import datetime
import csv
import subprocess
from config import LOG_FILE, RULES
from alerts import send_alert

is_protocol_active = False

import config

def not_work_after_protocol_activated(wa_client, ig_client):
    msg = config.MESSAGES.get("PROTOCOL_FAILED", "[PROTOCOL FAILED] The user failed to complete the required amount of productive work. Protocol triggered.")
    send_alert(msg, wa_client, ig_client, take_screenshot=True, custom_targets=config.SUMMARY_WHATSAPP_TARGETS)

def protocol_thread(wa_client, ig_client):
    global is_protocol_active
    start_time = datetime.datetime.now()
    
    # 1. Send the initial message
    initial_msg = (
        "Work is now mandatory.\n\n"
        'If you don\'t complete at least 40 minutes of productive work within the next hour, I am authorized to activate "not_work_after_protocol_activated()".\n\n'
        "I hope you understand what that means.\n\n"
        "Ever stop to think what Miss would think after receiving that message?"
    )
    send_alert(initial_msg, wa_client, ig_client, take_screenshot=False, custom_targets=config.SUMMARY_WHATSAPP_TARGETS)
    try:
        subprocess.run(['notify-send', '-u', 'critical', '🚨 MANDATORY WORK PROTOCOL ACTIVATED', 'You have 1 hour to complete 40 mins of work.'])
    except:
        pass
        
    cutoff_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
    
    for i in range(1, 7): # 6 checks, 10 minutes each
        time.sleep(600)
        
        productive_secs = 0
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 3:
                        try:
                            ts = row[0]
                            title = row[1] if len(row) == 3 else " ".join(row[1:-1])
                            duration = int(row[-1])
                        except:
                            continue
                        
                        if ts >= cutoff_str:
                            title_lower = title.lower()
                            is_prod = False
                            for cat in ["coding", "research"]:
                                for kw in RULES[cat]["keywords"]:
                                    if kw in title_lower:
                                        is_prod = True
                                        break
                                if is_prod: break
                                
                            if is_prod:
                                productive_secs += duration
        except Exception as e:
            print(f"Error reading LOG_FILE in protocol: {e}")
            
        if productive_secs >= 2400:  # 40 minutes = 2400 seconds
            success_msg = "Protocol Satisfied Early! 40 minutes of productive work detected. The Mandatory Protocol is deactivated."
            send_alert(success_msg, wa_client, ig_client, take_screenshot=False, custom_targets=config.SUMMARY_WHATSAPP_TARGETS)
            try:
                subprocess.run(['notify-send', '-u', 'normal', '✅ PROTOCOL COMPLETE', 'You finished your 40 minutes of work!'])
            except:
                pass
            is_protocol_active = False
            return
            
        if i < 6:
            mins_left = 60 - (i * 10)
            work_done = productive_secs // 60
            work_needed = 40 - work_done
            try:
                subprocess.run(['notify-send', '-u', 'critical', f'⏳ Protocol Update: {mins_left}m remaining', f'Work logged: {work_done} mins.\nYou still need {work_needed} mins of work.'])
            except:
                pass
                
    if productive_secs < 2400:
        not_work_after_protocol_activated(wa_client, ig_client)
    else:
        success_msg = "Protocol Satisfied: 40 minutes of productive work detected. The Mandatory Protocol is deactivated."
        send_alert(success_msg, wa_client, ig_client, take_screenshot=False, custom_targets=config.SUMMARY_WHATSAPP_TARGETS)

    is_protocol_active = False

def start_mandatory_protocol(wa_client, ig_client):
    global is_protocol_active
    if is_protocol_active:
        return # Don't start multiple protocols at once
        
    is_protocol_active = True
    threading.Thread(target=protocol_thread, args=(wa_client, ig_client), daemon=True).start()
