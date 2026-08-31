import os
import datetime
import matplotlib.pyplot as plt

def generate_progress_chart_v1(history_data, output_path):
    try:
        dates = []
        scores = []
        for item in history_data[-7:]:
            dates.append(item['date'])
            scores.append(item['score'])
            
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 4))
        
        ax.plot(dates, scores, color='#b28dff', marker='o', linewidth=2, markersize=6)
        ax.fill_between(dates, scores, color='#b28dff', alpha=0.2)
        
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        ax.set_ylim(0, 100) 
        ax.set_yticks([]) 
        ax.grid(False)
        
        x_labels = []
        for i in range(len(dates)):
            if i == len(dates) - 1:
                x_labels.append("Today")
            else:
                x_labels.append(f"D-{len(dates) - 1 - i}")
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(x_labels, color='gray', fontsize=9)
        
        fig.patch.set_facecolor('#1a1025')
        ax.set_facecolor('#1a1025')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()
        return output_path
    except Exception as e:
        print(f"Failed to generate chart: {e}")
        return None

# Create dummy history
history = []
base_date = datetime.date.today() - datetime.timedelta(days=7)
scores = [40, 80, 90, 100, 30, 70, 90]

for i, score in enumerate(scores):
    date_str = str(base_date + datetime.timedelta(days=i))
    history.append({
        'date': date_str,
        'score': score
    })

output_path = "/home/linuxayan/.gemini/antigravity-ide/brain/51448ef3-282f-4766-aa2d-35d762f40fdb/dummy_chart_v1.png"
generate_progress_chart_v1(history, output_path)
print(f"Chart saved to {output_path}")
