import time
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from instagram import Instagram

# ==========================================
# CONFIGURATION
# ==========================================
CHECK_INTERVAL_SECONDS = 60 # How often to check for new messages
AUTO_REPLY_MESSAGE = "Automated Reply: I'm currently away or busy, but I've received your message and will reply as soon as I can!"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(SCRIPT_DIR, "..", "data", "replied_ig_messages.json")

class IGAutoResponder:
    def __init__(self):
        self.ig = Instagram()
        self.replied_messages = self._load_state()

    def _load_state(self):
        """Loads the record of messages we have already replied to."""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[-] Error loading state file: {e}")
                return {}
        return {}

    def _save_state(self):
        """Saves the record of messages we have replied to."""
        try:
            with open(STATE_FILE, "w") as f:
                json.dump(self.replied_messages, f, indent=4)
        except Exception as e:
            print(f"[-] Error saving state file: {e}")

    def run(self):
        print("[*] Starting Instagram Auto-Responder...")
        
        # Ensure we are logged in
        if not self.ig._login():
            print("[-] Cannot start auto-responder because login failed.")
            return

        my_user_id = str(self.ig.client.user_id)
        print(f"[*] Successfully logged in. My User ID: {my_user_id}")
        print(f"[*] Auto-reply message: '{AUTO_REPLY_MESSAGE}'")
        print(f"[*] Checking for messages every {CHECK_INTERVAL_SECONDS} seconds...")

        while True:
            try:
                # Fetch unread threads
                threads = self.ig.get_unread_threads(amount=10)
                
                for thread in threads:
                    thread_id = str(thread.id)
                    
                    # Get the most recent message in the thread
                    if not thread.messages:
                        continue
                        
                    last_message = thread.messages[0]
                    message_id = str(last_message.id)
                    sender_id = str(last_message.user_id)
                    
                    # 1. Skip if the last message was sent by us
                    if sender_id == my_user_id:
                        continue
                        
                    # 2. Skip if we've already replied to this specific message
                    if thread_id in self.replied_messages and self.replied_messages[thread_id] == message_id:
                        continue

                    # 3. We have a new message to reply to!
                    print(f"\n[!] New unread message detected in thread {thread_id} from user {sender_id}")
                    print(f"[!] Message text: {last_message.text}")
                    
                    # Send the reply
                    success = self.ig.reply_to_thread(thread_id, AUTO_REPLY_MESSAGE)
                    
                    if success:
                        # Record that we've replied to this message so we don't do it again
                        self.replied_messages[thread_id] = message_id
                        self._save_state()
                        
            except Exception as e:
                print(f"[-] Error during polling cycle: {e}")
                
            # Wait before checking again
            time.sleep(CHECK_INTERVAL_SECONDS)

if __name__ == "__main__":
    responder = IGAutoResponder()
    try:
        responder.run()
    except KeyboardInterrupt:
        print("\n[*] Stopping auto-responder. Goodbye!")
