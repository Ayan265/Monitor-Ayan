import sys
sys.path.append('/home/linuxayan/Desktop/Monitor_ayan')
from monitor import generate_ai_summary, get_top_time_sinks

pc_total_time, mobile_total_time, top_pc_apps, top_mobile_apps, wasted_details = get_top_time_sinks()

print("Generating...")
output = generate_ai_summary(top_pc_apps, top_mobile_apps)
print("\n=== AI OUTPUT ===\n")
print(output)
