import os
import json
import datetime
import sys

# Add path so we can import the generator
sys.path.append("/home/linuxayan/Desktop/Monitor_ayan")
from monitor import generate_progress_chart

# Create dummy history
history = []
base_date = datetime.date.today() - datetime.timedelta(days=7)
current_price = 100.0

# Mix of bad, good, great, terrible, okay, great days
scores = [40, 80, 90, 100, 30, 70, 90]

for i, score in enumerate(scores):
    date_str = str(base_date + datetime.timedelta(days=i))
    change = (score - 50)
    current_price += change
    if current_price < 0:
        current_price = 0
    history.append({
        'date': date_str,
        'score': score,
        'price': current_price
    })

output_path = "/home/linuxayan/.gemini/antigravity-ide/brain/51448ef3-282f-4766-aa2d-35d762f40fdb/dummy_chart.png"
generate_progress_chart(history, output_path)
print(f"Chart saved to {output_path}")
