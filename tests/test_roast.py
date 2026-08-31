import json
import datetime
from monitor import send_daily_summary
from whatsapp import WhatsApp

# Mock time spent
time_spent = {
    "coding": 60 * 60 * 2, # 2 hours
    "bad_habit": 0,
    "anime_manga": 60 * 60 * 4 # 4 hours wasted
}

# Use yesterday to force trigger
target_date_str = str(datetime.date.today() - datetime.timedelta(days=1))

wa = WhatsApp()

print("Triggering test daily summary...")
send_daily_summary(time_spent, wa, None, target_date_str=target_date_str)
