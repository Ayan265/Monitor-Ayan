import os
import sys
import getpass
from instagrapi import Client

SETTINGS_FILE = os.path.expanduser("~/.ig_settings.json")

def setup():
    print("="*50)
    print("   Instagram Android Session Setup (instagrapi)")
    print("="*50)
    print("\nThis script will log into your Instagram account and generate")
    print(f"a completely valid Android session file at: {SETTINGS_FILE}")
    print("This file will be used by Monitor_ayan and ig_poller to avoid bans.\n")
    
    username = input("Instagram Username: ").strip()
    password = getpass.getpass("Instagram Password: ").strip()
    
    if not username or not password:
        print("[-] Username and password are required.")
        sys.exit(1)
        
    cl = Client()
    
    # Try to load existing settings if they exist to avoid triggering suspicious login
    if os.path.exists(SETTINGS_FILE):
        print(f"[*] Found existing settings at {SETTINGS_FILE}, loading them...")
        cl.load_settings(SETTINGS_FILE)
        
    print("[*] Attempting to log in via Android API...")
    try:
        cl.login(username, password)
        print("[+] Login successful!")
        
        # Save the session footprint
        cl.dump_settings(SETTINGS_FILE)
        print(f"[+] Android session saved successfully to {SETTINGS_FILE}")
        
    except Exception as e:
        print(f"[-] Login failed: {e}")
        print("Note: If it asks for 2FA or checkpoint verification, you may need to approve the login on your phone.")

if __name__ == "__main__":
    setup()
