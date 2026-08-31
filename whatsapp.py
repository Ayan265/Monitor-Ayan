import requests
import subprocess
import time
import os
import sys
import threading

class WhatsApp:
    def __init__(self, backend_url="http://localhost:3001"):
        self.backend_url = backend_url
        self._init_stuck_since = None
        self._last_force_restart = 0
        self._last_qr_popup = 0
        self._restart_lock = threading.Lock()
        
    def start_client(self):
        try:
            resp = requests.post(f"{self.backend_url}/start", timeout=5)
            data = resp.json()
            if data.get("status") == "already_initializing":
                self._check_and_heal()
            return True
        except requests.exceptions.ConnectionError:
            print("[HEAL] WA microservice not reachable. Attempting force restart...")
            self.force_restart()
            return True
        except Exception:
            return False
            
    def stop_client(self):
        try:
            requests.post(f"{self.backend_url}/stop", timeout=5)
            return True
        except:
            return False

    def is_ready(self):
        try:
            resp = requests.get(f"{self.backend_url}/status", timeout=3)
            data = resp.json()
            
            ready = data.get("ready", False)
            initializing = data.get("initializing", False)
            needs_qr = data.get("needsQRScan", False)
            init_elapsed = data.get("initElapsedMs", None)
            
            if ready:
                self._init_stuck_since = None
                return True
            
            if needs_qr:
                if time.time() - self._last_qr_popup > 60:
                    print("[!] WhatsApp needs QR re-scan. Popping up QR code...")
                    try:
                        subprocess.run(['notify-send', '-u', 'critical', '🚨 WhatsApp Session Expired', 'Scan the QR code to restore Accountability Monitor!'])
                        subprocess.Popen(['xdg-open', '/tmp/whatsapp_qr.png'])
                    except Exception as e:
                        pass
                    self._last_qr_popup = time.time()
                return False
            
            if not ready and not initializing:
                print("[!] WhatsApp backend seems idle/restarted. Re-triggering boot...")
                self.start_client()
                return False
            
            if initializing and init_elapsed and init_elapsed > 120000:
                print(f"[HEAL] WA stuck initializing for {init_elapsed//1000}s. Force restarting...")
                self.force_restart()
                return False
                
            return False
        except requests.exceptions.ConnectionError:
            print("[HEAL] WA microservice unreachable in is_ready(). Force restarting...")
            self.force_restart()
            return False
        except:
            return False

    def force_restart(self):
        with self._restart_lock:
            if time.time() - self._last_force_restart < 120:
                print("[HEAL] Force restart on cooldown. Skipping...")
                return
            self._last_force_restart = time.time()
            
            print("[HEAL] === FORCE RESTART: Killing all WA/Chrome processes ===")
            
            try: subprocess.run(['pkill', '-9', '-f', 'wa_backend'], capture_output=True, timeout=5)
            except: pass
            
            try: subprocess.run(['pkill', '-9', '-f', 'chromium.*wwebjs'], capture_output=True, timeout=5)
            except: pass
            
            try: subprocess.run(['pkill', '-9', '-f', '\\.wwebjs_auth/session'], capture_output=True, timeout=5)
            except: pass
            
            # Clean stale Chrome lock files
            session_dir = '/home/ayan/dev/WhatsApp_Service/.wwebjs_auth/session'
            for lock_file in ['SingletonLock', 'SingletonCookie', 'SingletonSocket']:
                lock_path = os.path.join(session_dir, lock_file)
                try:
                    if os.path.exists(lock_path):
                        os.unlink(lock_path)
                        print(f"[HEAL] Removed stale lock: {lock_file}")
                except: pass
            
            time.sleep(3)
            
            print("[HEAL] Starting fresh wa_backend.js in WhatsApp_Service...")
            try:
                wa_dir = '/home/ayan/dev/WhatsApp_Service'
                with open('/tmp/wa_backend.log', 'w') as log_file:
                    subprocess.Popen(
                        ['/home/ayan/.nvm/versions/node/v20.20.2/bin/node', 'wa_backend.js'],
                        cwd=wa_dir,
                        stdout=log_file,
                        stderr=log_file,
                        start_new_session=True
                    )
                print("[HEAL] wa_backend.js process started. Waiting for port...")
                
                for i in range(15):
                    time.sleep(2)
                    try:
                        resp = requests.get(f"{self.backend_url}/health", timeout=2)
                        if resp.status_code == 200:
                            print(f"[HEAL] Backend alive after {(i+1)*2}s. Triggering /start...")
                            requests.post(f"{self.backend_url}/start", timeout=5)
                            return True
                    except:
                        pass
                
                print("[HEAL] Backend didn't come up after 30s.")
                return False
            except Exception as e:
                print(f"[HEAL] Failed to start wa_backend.js: {e}")
                return False

    def _check_and_heal(self):
        try:
            resp = requests.get(f"{self.backend_url}/status", timeout=3)
            data = resp.json()
            init_elapsed = data.get("initElapsedMs", None)
            needs_qr = data.get("needsQRScan", False)
            
            if needs_qr:
                if time.time() - self._last_qr_popup > 60:
                    print("[!] WhatsApp needs QR re-scan. Popping up QR code...")
                    try:
                        subprocess.run(['notify-send', '-u', 'critical', '🚨 WhatsApp Session Expired', 'Scan the QR code to restore Accountability Monitor!'])
                        subprocess.Popen(['xdg-open', '/tmp/whatsapp_qr.png'])
                    except Exception as e: pass
                    self._last_qr_popup = time.time()
                return
            
            if init_elapsed and init_elapsed > 90000:
                print(f"[HEAL] Init stuck for {init_elapsed//1000}s. Triggering force_restart via API...")
                try: requests.post(f"{self.backend_url}/force_restart", timeout=5)
                except: self.force_restart()
        except:
            pass

    def send_alert_msg(self, phone_number, message, image_path=None, audio_path=None, delete_locally=False):
        print(f"[*] Asking backend to send WhatsApp ALERT to {phone_number}...")
        
        # We now map arguments to the generalized microservice payload
        payload = {
            "target": phone_number, 
            "message": message,
            "delete_locally": delete_locally
        }

        if audio_path:
            payload["media_path"] = audio_path
            payload["as_voice"] = True
            
            if audio_path.lower().endswith('.wav'):
                ogg_path = "/tmp/wa_voice_msg.ogg"
                try:
                    subprocess.run(["ffmpeg", "-y", "-i", audio_path, "-c:a", "libopus", "-b:a", "32k", ogg_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                    payload["media_path"] = ogg_path
                except Exception as e: print(f"[-] Failed to convert WAV to OGG: {e}")
        elif image_path:
            payload["media_path"] = image_path
            payload["as_voice"] = False

        try:
            response = requests.post(f"{self.backend_url}/send_message", json=payload, timeout=15)
            data = response.json()
            if response.status_code == 200:
                print("[+] Alert message sent successfully!")
                return True
            elif response.status_code == 503 and data.get("needsQRScan"):
                print("[!] WhatsApp session expired. QR re-scan needed.")
                return False
            else:
                print(f"[-] Backend error: {data.get('error', 'Unknown Error')}")
                print("[HEAL] Backend returned error during send_alert. Triggering force_restart...")
                self.force_restart()
                return False
        except Exception as e:
            print("[-] Error: Could not connect to the NodeJS Backend.")
            self.force_restart()
            return False

    def send_summary_msg(self, phone_number, message, image_path=None):
        print(f"[*] Asking backend to send WhatsApp SUMMARY to {phone_number}...")
        payload = {"target": phone_number, "message": message}
        if image_path:
            payload["media_path"] = image_path
            payload["as_voice"] = False
            
        try:
            response = requests.post(f"{self.backend_url}/send_message", json=payload, timeout=15)
            data = response.json()
            if response.status_code == 200:
                print("[+] Summary message sent successfully!")
                return True
            elif response.status_code == 503 and data.get("needsQRScan"):
                print("[!] WhatsApp session expired. QR re-scan needed.")
                return False
            else:
                print(f"[-] Backend error: {data.get('error', 'Unknown Error')}")
                print("[HEAL] Backend returned error during send_summary. Triggering force_restart...")
                self.force_restart()
                return False
        except Exception as e:
            print("[-] Error: Could not connect to the NodeJS Backend.")
            self.force_restart()
            return False
