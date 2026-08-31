# Accountability Monitor 🛡️

An automated, relentless, AI-powered desktop accountability monitor designed to track productivity, enforce discipline, and prevent bad habits. 

It runs silently in the background of your Linux machine, monitoring active windows. If it detects time-wasting or restricted activities, it immediately escalates the situation by sending alerts to an accountability partner via WhatsApp and Instagram Direct Messages. At the end of the day, it generates a comprehensive AI-driven performance report using Google's Gemini API.

## ✨ Features
*   **Real-time Window Tracking**: Silently monitors active application titles using Linux APIs.
*   **Multi-Tiered Escalation**: Sends increasingly severe warnings based on the duration of the distraction.
*   **Mandatory Work Protocols**: Enforces productivity blocks (e.g., locking you in until you complete 40 minutes of coding).
*   **WhatsApp Integration**: Uses `whatsapp-web.js` to send instant messages and screenshots to accountability groups.
*   **Instagram Integration**: Uses `instagrapi` to send silent DMs without triggering 2FA or suspicious login locks.
*   **AI Daily Reports**: Leverages Google Gemini to analyze your daily activity CSV and generate a customized, brutally honest summary of your day.

## 🚀 Setup

### 1. Install Dependencies
This project requires both Python 3 and Node.js.

```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies (for WhatsApp backend)
npm install
```

### 2. Configure Your Secrets
For privacy and security, this project uses a `private/` directory that is strictly ignored by Git. You must create this file before running the program.

Create a file at `private/secrets.json`:
```json
{
    "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY",
    "SUMMARY_WHATSAPP_TARGETS": ["Your Summary Group Name"],
    "ALERT_WHATSAPP_TARGETS": ["Your Alert Group Name"],
    "WA_TARGET_ID_CACHE": {
        "Your Alert Group Name": "1234567890@g.us"
    },
    "IG_TARGET_USERNAME": "friends_instagram_handle"
}
```

### 3. Run the Monitor
```bash
python3 main.py
```
On the first run, the WhatsApp backend will generate a QR code in the terminal. Scan it with your WhatsApp mobile app to link the session.

## 📁 Architecture
- `main.py`: Entry point that spawns the tracker and backends.
- `core_tracker.py`: Tracks window titles and logs activity to CSV.
- `alerts.py`: Orchestrates messaging and screenshots.
- `wa_backend.js`: Headless WhatsApp Web client.
- `ai_reports.py`: Generates the end-of-day summary using Gemini.
- `private/`: **(Ignored)** Your local secrets and custom rules.

## ⚠️ Disclaimer
This script is designed for extreme personal accountability. It takes screenshots and sends them to third parties automatically. Use at your own risk and ensure your accountability partners consent to receiving automated messages.
