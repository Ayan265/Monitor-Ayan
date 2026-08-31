import os
import datetime
from monitor import generate_progress_chart

# Create dummy history
history = []
base_date = datetime.date.today() - datetime.timedelta(days=7)
scores = [40, 80, 90, 100, 30, 70, 90]

for i, score in enumerate(scores):
    date_str = str(base_date + datetime.timedelta(days=i))
    history.append({
        'date': date_str,
        'price': score
    })

output_path = "/home/linuxayan/.gemini/antigravity-ide/brain/51448ef3-282f-4766-aa2d-35d762f40fdb/dummy_chart_v2.png"
generate_progress_chart(history, output_path)
print(f"Chart saved to {output_path}")
