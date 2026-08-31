import os

class Instagram:
    """
    Python wrapper for sending Instagram Direct Messages using your existing session ID.
    This safely skips the username/password login step and avoids 2FA / suspicious login locks.
    """
    def __init__(self, session_file="~/.ig_session"):
        self.session_file = os.path.expanduser(session_file)
        self.client = None
        
    def start_client(self):
        """Pre-loads the Instagram client into memory (JIT)."""
        return self._login()
        
    def stop_client(self):
        """Clears the Instagram client from memory to prevent 24/7 background polling."""
        if self.client:
            print("[*] Shutting down Instagram client to save memory...")
            self.client = None
            
    def _login(self):
        if self.client is not None:
            return True # Already logged in
            
        if not os.path.exists(self.session_file):
            print(f"[-] Error: Session file not found at {self.session_file}")
            return False
            
        with open(self.session_file, 'r') as f:
            sessionid = f.read().strip()
            
        settings_file = os.path.expanduser("~/.ig_settings.json")
        try:
            from instagrapi import Client
            self.client = Client()
            
            if os.path.exists(settings_file):
                print("[*] Loading Instagram device settings...")
                self.client.load_settings(settings_file)
                
            print("[*] Resuming Instagram session from ~/.ig_session...")
            # This logs in using the sessionid
            self.client.login_by_sessionid(sessionid)
            
            # Save settings (device uuid, cookies, etc.) to prevent session invalidation
            self.client.dump_settings(settings_file)
            
            print("[+] Successfully connected to Instagram!")
            return True
        except Exception as e:
            print(f"[-] Failed to connect to Instagram: {e}")
            return False

    def send_message(self, target_username, message, image_path=None):
        """
        Sends an Instagram DM to a specific username.
        """
        if not self._login():
            return False
            
        try:
            print(f"[*] Looking up user ID for @{target_username}...")
            user_id = self.client.user_id_from_username(target_username)
            print(f"[*] Sending message to @{target_username}...")
            
            if image_path and os.path.exists(image_path):
                self.client.direct_send_photo(image_path, user_ids=[user_id])
                print(f"[+] Successfully sent photo to @{target_username}")
                
            msg = self.client.direct_send(message, user_ids=[user_id])
            print(f"[+] Successfully sent IG DM to {target_username}")
            
            # We are sending the message normally here. 
            # Because Instagram does not truly support "Delete for me only" (it unsends for everyone),
            # we leave the chat exactly as is so your chat history remains safe and your friend receives the alert!
                
            return True
        except Exception as e:
            print(f"[-] Failed to send IG DM: {e}")
            return False

    def get_unread_threads(self, amount=20):
        """
        Fetches unread message threads from the inbox.
        Returns a list of thread objects.
        """
        if not self._login():
            return []
            
        try:
            print("[*] Fetching unread threads...")
            # 'selected_filter="unread"' ensures we only get threads with unread messages
            threads = self.client.direct_threads(amount=amount, selected_filter="unread")
            return threads
        except Exception as e:
            print(f"[-] Failed to fetch unread threads: {e}")
            return []

    def reply_to_thread(self, thread_id, message):
        """
        Sends a reply to an existing thread by its ID.
        """
        if not self._login():
            return False
            
        try:
            print(f"[*] Replying to thread {thread_id}...")
            self.client.direct_send(message, thread_ids=[thread_id])
            print(f"[+] Successfully replied to thread {thread_id}")
            return True
        except Exception as e:
            print(f"[-] Failed to reply to thread: {e}")
            return False

# ==========================================
# HOW TO USE IT
# ==========================================
if __name__ == "__main__":
    # 1. Initialize
    ig = Instagram()
    
    target_username = "target_username"
    try:
        import json
        secrets_path = os.path.join(os.path.dirname(__file__), "private", "secrets.json")
        if os.path.exists(secrets_path):
            with open(secrets_path, "r") as f:
                secrets = json.load(f)
                target_username = secrets.get("IG_TARGET_USERNAME", target_username)
    except:
        pass
        
    # 2. Send a message
    # ig.send_message(target_username, "Hello! This is an invisible automated IG alert from my monitor.")
    
    print("Open instagram.py and uncomment the line above to test it!")
