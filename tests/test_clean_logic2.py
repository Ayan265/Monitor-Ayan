def clean_title(title):
    clean_title = title.strip().title()
    if " - " in clean_title:
        parts = [p.strip() for p in clean_title.split(" - ")]
        if len(parts) >= 2:
            clean_title = f"{parts[0]}: {parts[-1]}"
    elif " | " in clean_title:
        parts = [p.strip() for p in clean_title.split(" | ")]
        if len(parts) >= 2:
            clean_title = f"{parts[0]}: {parts[-1]}"
            
    # Cap length
    short_title = clean_title[:35] + "..." if len(clean_title) > 35 else clean_title
    return short_title

titles = [
    "Monitor_Ayan - Antigravity - Implementation Plan",
    "Monitor_Ayan - Antigravity - Mobile_Webhook.Py",
    "Ayan | Syncthing",
    "Accountability Audit Review",
    "Apollo Tyres Research Audit"
]

for t in titles:
    print(f"Original: {t}")
    print(f"Cleaned : {clean_title(t)}\n")
