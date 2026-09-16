import time
import subprocess
import datetime
import os
import json
import logging
import threading
from config import (
    QUEUE_FILE,
    ALERT_WHATSAPP_TARGETS,
    ALERT_IG_USERNAMES,
    log
)

queue_lock = threading.Lock()


def queue_failed_message(message, platform, target, image_path=None):
    """Save a failed message to the vault to be retried later."""
    with queue_lock:
        queue = []
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, "r") as f:
                    queue = json.load(f)
            except Exception:
                pass
                
        if not message.endswith("⏳ *(Delayed Delivery)*"):
            message = f"{message}\n\n⏳ *(Delayed Delivery)*"
            
        queue.append({
            "timestamp": str(datetime.datetime.now()),
            "message": message,
            "platform": platform,
            "target": target,
            "image_path": image_path
        })
        
        try:
            with open(QUEUE_FILE, "w") as f:
                json.dump(queue, f, indent=4)
            log.info(f"Queued failed {platform} message for {target}")
        except Exception as e:
            log.error(f"Failed to queue message: {e}")


def retry_failed_messages(wa_client, ig_client):
    """Attempt to flush the message vault."""
    if not os.path.exists(QUEUE_FILE):
        return
        
    try:
        with queue_lock:
            with open(QUEUE_FILE, "r") as f:
                queue = json.load(f)
                
            if not queue:
                return
                
            # Clear the file since we grabbed everything
            with open(QUEUE_FILE, "w") as f:
                json.dump([], f)
                
        print(f"[*] Found {len(queue)} messages in the Vault. Attempting retry...")
        log.info(f"Attempting to retry {len(queue)} queued messages.")
        
        wa_started = False
        
        for item in queue:
            success = False
            platform = item.get("platform")
            target = item.get("target")
            msg = item.get("message")
            image_path = item.get("image_path")
            
            if image_path and not os.path.exists(image_path):
                log.warning(f"Image {image_path} missing from disk. Stripping image from queued message.")
                image_path = None
                item["image_path"] = None
            
            if platform == "whatsapp" and wa_client:
                if not wa_started:
                    print("[*] Waiting for WhatsApp to be ready for queue processing...")
                    try:
                        wa_client.start_client()
                        wa_started = True
                        for _ in range(120):
                            if wa_client.is_ready():
                                break
                            time.sleep(1)
                    except Exception:
                        pass
                
                if wa_client.is_ready():
                    success = wa_client.send_summary_msg(target, msg, image_path)
            
            elif platform == "instagram" and ig_client:
                try:
                    success = ig_client.send_message(target, msg, image_path)
                except:
                    success = False
                    
            if not success:
                queue_failed_message(msg, platform, target, image_path)
                
    except Exception as e:
        log.error(f"Failed to process message queue: {e}")


def send_alert(message, wa_client, ig_client, take_screenshot=False, delete_locally=True, custom_image_path=None, block=False, custom_targets=None):
    """Send alerts to messengers. Failures here MUST NOT crash the monitor."""
    print(f"\n[!!!] TRIGGERING ALERT: {message}")
    log.info(f"ALERT TRIGGERED: {message}")
    
    image_path = custom_image_path
    if take_screenshot and not custom_image_path:
        try:
            image_path = f"/tmp/accountability_alert_{int(time.time())}.png"
            
            # Use the Wayland portal screenshot helper (runs with system python3)
            # This saves directly to our /tmp path — never touches ~/Pictures/Screenshots
            script_dir = os.path.dirname(os.path.abspath(__file__))
            ss_script = os.path.join(script_dir, "scripts", "wayland_screenshot.py")
            result = subprocess.run(
                ["/usr/bin/python3", ss_script, image_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and os.path.exists(image_path):
                print("[*] Wayland screenshot captured successfully.")
            else:
                print(f"[-] Screenshot failed: {result.stderr.strip()}")
                log.warning(f"Screenshot failed: {result.stderr.strip()}")
                image_path = None
        except Exception as e:
            print(f"[-] Failed to take screenshot: {e}")
            log.error(f"Failed to take screenshot: {e}")
            image_path = None

    def _network_send():
        if wa_client:
            try:
                # Ensure WA backend is started (the prompter thread doesn't
                # go through the main loop's JIT boot, so WA may be cold)
                try:
                    wa_client.start_client()
                except Exception:
                    pass

                # Wait for WA to finish booting
                print("[*] Waiting for WhatsApp to be ready...")
                for i in range(120):  # Poll for up to 120 seconds
                    if wa_client.is_ready():
                        break
                    time.sleep(1)
                
                if wa_client.is_ready():
                    targets = custom_targets if custom_targets is not None else ALERT_WHATSAPP_TARGETS
                    for num in targets:
                        success = wa_client.send_alert_msg(num, message, image_path, delete_locally=delete_locally)
                        if not success:
                            queue_failed_message(message, "whatsapp", num, image_path)
                else:
                    log.error("WhatsApp not ready after 120s — alert NOT sent via WA")
                    print("[-] WhatsApp not ready after 120s — skipping WA alert")
                    targets = custom_targets if custom_targets is not None else ALERT_WHATSAPP_TARGETS
                    for num in targets:
                        queue_failed_message(message, "whatsapp", num, image_path)
            except Exception as e:
                log.error(f"WhatsApp alert failed: {e}")
                print(f"[-] WhatsApp alert failed: {e}")
                targets = custom_targets if custom_targets is not None else ALERT_WHATSAPP_TARGETS
                for num in targets:
                    queue_failed_message(message, "whatsapp", num, image_path)

        if ig_client:
            try:
                for user in ALERT_IG_USERNAMES:
                    try:
                        success = ig_client.send_message(user, message, image_path)
                        if success is False: # Depending on instagrapi return
                            queue_failed_message(message, "instagram", user, image_path)
                    except Exception as ig_err:
                        queue_failed_message(message, "instagram", user, image_path)
            except Exception as e:
                log.error(f"Instagram alert failed globally: {e}")
                print(f"[-] Instagram alert failed globally: {e}")
                try:
                    subprocess.run(['notify-send', '-u', 'critical', '⚠️ IG SESSION FAILED', 'Your Instagram login expired! Check monitor.log'])
                except Exception:
                    pass

    # Run the network sending in the background so the main monitor loop NEVER freezes or misses seconds
    t = threading.Thread(target=_network_send, daemon=not block)
    t.start()
    if block:
        t.join()