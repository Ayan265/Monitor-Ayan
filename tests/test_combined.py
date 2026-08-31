import sys
import os
sys.path.append('/home/linuxayan/Desktop/Monitor_ayan')
from monitor import get_top_time_sinks

total_time, top_apps, wasted_details = get_top_time_sinks()

print(f"Total Time: {total_time / 3600:.1f} hours")
print("\nTop Sinks Currently Being Sent to WhatsApp:")
for app, duration in top_apps:
    print(f" - {app}: {duration/60:.1f} minutes")
