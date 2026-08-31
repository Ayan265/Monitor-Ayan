import requests
import json

print("[*] Fetching all available ActivityWatch buckets...\n")

try:
    url = "http://localhost:5600/api/0/buckets"
    response = requests.get(url)
    
    if response.status_code == 200:
        buckets = response.json()
        
        for bucket_id, bucket_info in buckets.items():
            print(f"=== BUCKET: {bucket_id} ===")
            print(f"Type: {bucket_info.get('type')}")
            print(f"Client: {bucket_info.get('client')}")
            
            # Fetch exactly 1 event from this bucket to see its structure
            event_url = f"http://localhost:5600/api/0/buckets/{bucket_id}/events"
            event_res = requests.get(event_url, params={"limit": 1})
            
            if event_res.status_code == 200:
                events = event_res.json()
                if events:
                    print("Example Data Point:")
                    print(json.dumps(events[0], indent=4))
                else:
                    print("Example Data Point: [No events recorded yet]")
            print("\n")
            
    else:
        print(f"[-] Failed to fetch buckets: {response.text}")
except Exception as e:
    print(f"[-] Error connecting to ActivityWatch: {e}")
