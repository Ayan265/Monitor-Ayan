
# Monitor Accountability Rules
- **WhatsApp Backend**: The WhatsApp backend (Node.js) sometimes suffers from Puppeteer bugs like "detached Frame". Do NOT remove the auto-healing logic in `whatsapp.py` (`self.force_restart()`) that restarts the backend when a request fails or returns an error.
- **AI Summary Fallback**: Do NOT remove the fallback logic in `ai_reports.py` (which uses `time_spent` dictionaries). The Gemini API may occasionally fail due to temporary DNS or quota issues; the system MUST be able to send summaries without AI. 
