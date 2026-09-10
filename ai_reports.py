import time
import subprocess
import datetime
import os
import json
import logging
import requests
import csv
import re
import config
from config import (
    GEMINI_API_KEY,
    SUMMARY_WHATSAPP_TARGETS,
    ALERT_IG_USERNAMES,
    RULES,
    LOG_FILE,
    SCRIPT_DIR,
    log
)
from data_manager import get_top_time_sinks, get_weekly_time_sinks, update_and_get_daily_scores
from alerts import send_alert, queue_failed_message
from web_server import get_logical_today


def analyze_time_with_ai(top_pc_apps, top_mobile_apps):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""You are an accountability AI. I will give you a list of apps and window titles Ayan used today across his laptop and mobile.
Your job is to categorize this time into Productive Work or Wasted Time.
Productive usually includes: Coding, IDEs (VS Code), Terminals, Research (Audits, PDF reading), Syncthing, System tools.
Wasted usually includes: Social Media (Instagram, WhatsApp, Facebook), Entertainment (Moviebox, YouTube), Browsing, Games.
CRITICAL RULE FOR WINDOWS OS: Any app starting with "[Win]" is guaranteed to be WASTED TIME (mostly gaming) UNLESS it is Firefox (marked as "[Win Firefox]"), in which case you must judge based on the URL/Title. Otherwise, if the app name contains "Youtube", "Instagram", "Capcut", or "Proton Vpn", these are productive for video editing/posting.

LAPTOP TIME:
{', '.join([f"{app} ({secs//60}m)" for app, secs in top_pc_apps])}

MOBILE TIME:
{', '.join([f"{app} ({secs//60}m)" for app, secs in top_mobile_apps])}
"""
    
    schema = {
        "type": "object",
        "properties": {
            "productive_minutes": {"type": "integer"},
            "productive_breakdown": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "app": {"type": "string"},
                        "minutes": {"type": "integer"}
                    },
                    "required": ["app", "minutes"]
                }
            },
            "wasted_minutes": {"type": "integer"},
            "wasted_breakdown": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "app": {"type": "string"},
                        "minutes": {"type": "integer"}
                    },
                    "required": ["app", "minutes"]
                }
            },
            "ai_verdict": {"type": "string"}
        },
        "required": ["productive_minutes", "productive_breakdown", "wasted_minutes", "wasted_breakdown", "ai_verdict"]
    }

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data), timeout=45)
            if response.status_code == 200:
                result = response.json()
                json_text = result['candidates'][0]['content']['parts'][0]['text']
                return json.loads(json_text)
            else:
                log.error(f"AI API Error (attempt {attempt+1}/3): {response.text}")
        except Exception as e:
            log.error(f"AI Call failed (attempt {attempt+1}/3): {e}")
        
        if attempt < 2:
            time.sleep(15)  # Wait 15 seconds before retrying
    return None


def analyze_weekly_with_ai(top_pc_apps, top_mobile_apps):
    # Reverting to gemini-2.5-flash to avoid strict Free-Tier Quota limits on the Pro model
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""You are a ruthless prosecutor. Treat this report like evidence in court proving Ayan betrayed his own goals. Prosecute him. Expose every excuse, mock every wasted minute, roast every distraction, and make his bad decisions sound ridiculous. Use sharp sarcasm, clever comparisons, and relentless mockery. Make it sting enough that reading it feels uncomfortable, but keep every criticism grounded in the data. Attack the behavior, never the person.

IMPORTANT: Write in simple, conversational English. Use short sentences. Avoid overly complex metaphors or vocabulary so it is very easy to read on a mobile screen.

I am providing aggregated data from the entire week.
Your job is to categorize this time into Productive Work or Wasted Time, and generate TWO separate text blocks:

1. `progress_roast`: Prosecute his "productive" work. Mock him for being slow, inefficient, or taking too long on simple tasks.
2. `wasted_roast`: Prosecute his wasted time and distractions mercilessly. Make him feel terrible.

Productive includes: Coding, IDEs, Terminals, Research, Syncthing.
Wasted includes: Social Media, Entertainment (Moviebox, YouTube), Browsing, Games.
CRITICAL RULE FOR WINDOWS OS: Any app starting with "[Win]" is guaranteed to be WASTED TIME (mostly gaming) UNLESS it is Firefox (marked as "[Win Firefox]"), in which case you must judge based on the URL/Title. Otherwise, if the app name contains "Youtube", "Instagram", "Capcut", or "Proton Vpn", these are productive for video editing/posting.

LAPTOP TIME (WEEKLY AGGREGATE):
{', '.join([f"{app} ({secs//3600}h {(secs%3600)//60}m)" for app, secs in top_pc_apps])}

MOBILE TIME (WEEKLY AGGREGATE):
{', '.join([f"{app} ({secs//3600}h {(secs%3600)//60}m)" for app, secs in top_mobile_apps])}
"""
    
    schema = {
        "type": "object",
        "properties": {
            "productive_minutes": {"type": "integer"},
            "productive_breakdown": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "app": {"type": "string"},
                        "minutes": {"type": "integer"}
                    },
                    "required": ["app", "minutes"]
                }
            },
            "wasted_minutes": {"type": "integer"},
            "wasted_breakdown": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "app": {"type": "string"},
                        "minutes": {"type": "integer"}
                    },
                    "required": ["app", "minutes"]
                }
            },
            "progress_roast": {"type": "string"},
            "wasted_roast": {"type": "string"}
        },
        "required": ["productive_minutes", "productive_breakdown", "wasted_minutes", "wasted_breakdown", "progress_roast", "wasted_roast"]
    }

    data = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema
        }
    }
    
    for attempt in range(3):
        try:
            response = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps(data), timeout=45)
            if response.status_code == 200:
                result = response.json()
                json_text = result['candidates'][0]['content']['parts'][0]['text']
                return json.loads(json_text)
            else:
                log.error(f"Weekly AI API Error (attempt {attempt+1}/3): {response.text}")
        except Exception as e:
            log.error(f"Weekly AI Call failed (attempt {attempt+1}/3): {e}")
        
        if attempt < 2:
            time.sleep(15)  # Wait 15 seconds before retrying
    return None


def send_weekly_summary(wa_client, ig_client):
    try:
        pc_total_time, mobile_total_time, top_pc_apps, top_mobile_apps = get_weekly_time_sinks()
        total_time = pc_total_time + mobile_total_time
        total_hours = round(total_time / 3600, 1)
        
        report_progress = "🗓️ *WEEKLY MACRO AUDIT (1/2)* 🗓️\n\n"
        report_progress += "━━━━━━━━━━━━━━━━━━\n"
        report_progress += f"🖥 Total Screen Time: {total_hours} hours\n\n"
        
        report_wasted = "🗓️ *WEEKLY MACRO AUDIT (2/2)* 🗓️\n\n"
        report_wasted += "━━━━━━━━━━━━━━━━━━\n"
        
        print("[*] Contacting Gemini AI PRO for WEEKLY categorization...")
        ai_data = analyze_weekly_with_ai(top_pc_apps, top_mobile_apps)
        
        if ai_data:
            prod_hours = round(ai_data['productive_minutes'] / 60, 1)
            report_progress += f"✅ Productive Work: {prod_hours} hours\n"
            for item in ai_data.get('productive_breakdown', [])[:8]:
                app_mins = item['minutes']
                dur_str = f"{round(app_mins / 60, 1)} hrs" if app_mins >= 60 else f"{app_mins} mins"
                report_progress += f"   • {item['app']} ({dur_str})\n"
            
            report_progress += "\n━━━━━━━━━━━━━━━━━━\n"
            report_progress += f"🧠 *AI MACRO VERDICT:*\n\n{ai_data['progress_roast']}\n"
            
            wasted_mins = ai_data['wasted_minutes']
            report_wasted += f"❌ Wasted Time: {wasted_mins // 60} hrs {wasted_mins % 60} mins\n\n"
            
            report_wasted += "Worst Distractions:\n"
            for item in ai_data.get('wasted_breakdown', [])[:8]:
                app_mins = item['minutes']
                dur_str = f"{round(app_mins / 60, 1)} hrs" if app_mins >= 60 else f"{app_mins} mins"
                report_wasted += f"   • {item['app']} ({dur_str})\n"
            
            report_wasted += "\n━━━━━━━━━━━━━━━━━━\n"
            report_wasted += f"🗑️ *WASTED TIME ROAST:*\n{ai_data['wasted_roast']}\n"
        else:
            report_progress += "\n[AI Analysis Failed. Missing Data.]\n"
            report_wasted += "\n[AI Analysis Failed. Missing Data.]\n"

        if wa_client:
            print("\n[*] JIT Booting WhatsApp for Weekly Summary...")
            try:
                wa_client.start_client()
            except Exception as e:
                log.error(f"WA start_client failed for weekly summary: {e}")
            
            # Wait for WA readiness
            for i in range(120):
                if wa_client.is_ready():
                    break
                time.sleep(1)
                
            if wa_client.is_ready():
                for target in SUMMARY_WHATSAPP_TARGETS:
                    print(f"[*] Asking backend to send WhatsApp WEEKLY SUMMARY to {target}...")
                    try:
                        success_1 = wa_client.send_summary_msg(target, report_progress)
                        time.sleep(2)
                        success_2 = wa_client.send_summary_msg(target, report_wasted)
                        
                        if success_1 and success_2:
                            print(f"[+] Both Weekly summaries sent to {target} successfully!")
                        else:
                            queue_failed_message(report_progress, "whatsapp", target)
                            queue_failed_message(report_wasted, "whatsapp", target)
                    except Exception as e:
                        log.error(f"WA weekly summary send crash for {target}: {e}")
                        queue_failed_message(report_progress, "whatsapp", target)
                        queue_failed_message(report_wasted, "whatsapp", target)
            else:
                log.error("WhatsApp not ready for weekly summary")
                for target in SUMMARY_WHATSAPP_TARGETS:
                    queue_failed_message(report_progress, "whatsapp", target)
                    queue_failed_message(report_wasted, "whatsapp", target)
                
            try:
                print("[*] Waiting 10 seconds for WhatsApp to sync message to your phone...")
                time.sleep(10)
                wa_client.stop_client()
            except Exception:
                pass
                
    except Exception as e:
        log.error(f"Failed to send weekly summary: {e}")


def generate_progress_chart(history_data, output_path="/tmp/progress_chart.png"):
    try:
        import matplotlib.pyplot as plt

        dates = []
        prices = []
        for item in history_data[-7:]:
            dates.append(item['date'])
            prices.append(item.get('price', 100))
            
        current_price = prices[-1] if prices else 100
        prev_price = prices[-2] if len(prices) > 1 else 100
        change = current_price - prev_price
        
        is_up = change >= 0
        number_color = '#00ff00' if is_up else '#ff3333'
        
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(8, 4))
        
        # Base neon line
        ax.plot(dates, prices, color='#b28dff', marker='o', linewidth=3, markersize=8, zorder=5)
        
        # Glow layers
        for n in range(1, 8):
            ax.plot(dates, prices, color='#b28dff', linewidth=3 + (n * 3), alpha=0.1 - (n * 0.01), zorder=4)
            
        ax.fill_between(dates, prices, color='#b28dff', alpha=0.15, zorder=3)
        
        # Floating price tags
        for i, price in enumerate(prices):
            ax.text(i, price + 0.5, f"{price:.1f}", color='white', 
                    ha='center', va='bottom', fontsize=9, fontweight='bold', zorder=6)
                    
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        
        # Add padding to zoom out the chart slightly
        if prices:
            p_min, p_max = min(prices), max(prices)
            margin = (p_max - p_min) * 0.4
            if margin == 0: margin = 20
            ax.set_ylim(p_min - margin, p_max + margin)
            
        ax.set_yticks([]) 
        ax.grid(False)
        
        x_labels = []
        for i in range(len(dates)):
            if i == len(dates) - 1:
                x_labels.append("Today")
            else:
                x_labels.append(f"D-{i+1}")
        ax.set_xticks(range(len(dates)))
        ax.set_xticklabels(x_labels, color='gray', fontsize=9)
        
        fig.patch.set_facecolor('#1a1025')
        ax.set_facecolor('#1a1025')
        
        fig.text(0.5, 0.5, 'AYAN PRICE CHART', fontsize=36, color='gray', 
                 ha='center', va='center', alpha=0.1, fontweight='bold')
                 
        sign = "+" if is_up else ""
        price_text = f"{current_price:.1f} pts ({sign}{change:.1f})"
        ax.text(0.02, 0.95, price_text, transform=ax.transAxes, fontsize=14, 
                color=number_color, fontweight='bold', va='top')
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
        plt.close()
        return output_path
    except Exception as e:
        log.error(f"Failed to generate chart: {e}")
        return None


def send_daily_summary(time_spent, wa_client, ig_client, target_date_str=None):
    """Sends an end-of-day summary message with chart and shuts down WA."""
    try:
        if not target_date_str:
            target_date_str = str(get_logical_today())

        pc_total_time, mobile_total_time, top_pc_apps, top_mobile_apps, wasted_details = get_top_time_sinks(target_date_str)

        ai_data = None
        if top_pc_apps or top_mobile_apps:
            print("[*] Contacting Gemini AI for time categorization...")
            ai_data = analyze_time_with_ai(top_pc_apps, top_mobile_apps)

        prod_mins = 0
        wasted_mins = 0
        if ai_data:
            prod_mins = ai_data.get('productive_minutes', 0)
            wasted_mins = ai_data.get('wasted_minutes', 0)
        else:
            # Fallback to old math if AI fails
            prod_mins = (time_spent.get('coding', 0) + time_spent.get('research', 0)) // 60
            bad_secs = time_spent.get('bad_habit', 0) + time_spent.get('anime_manga', 0)
            wasted_mins = bad_secs // 60

        total_tracked_mins = prod_mins + wasted_mins
        td_score = prod_mins - wasted_mins # Net productive minutes

        history = update_and_get_daily_scores(target_date_str, td_score)

        verdict = "Stagnant"
        if len(history) >= 2:
            yd_score = history[-2]['score']
            diff = td_score - yd_score
            if diff > 0 or td_score >= 120:
                verdict = "Improved"
            elif diff < 0 or td_score < 0:
                verdict = "Declined"
        else:
            if td_score >= 120:
                verdict = "Improved"
            elif td_score < 0:
                verdict = "Declined"

        prod_hours_str = f"{round(prod_mins / 60, 1)} hrs" if prod_mins >= 60 else f"{prod_mins} mins"
        wasted_hours_str = f"{round(wasted_mins / 60, 1)} hrs" if wasted_mins >= 60 else f"{wasted_mins} mins"

        report = "Daily accountability Audit\n"
        report += f"{target_date_str}\n"
        report += f"{verdict}\n"
        report += f"Productive Work : {prod_hours_str}\n"
        report += f"Wasted Time : {wasted_hours_str}\n"

        # --- SYSTEM CALCULATION ---
        roast_msg = ""
        current_price = history[-1]['price'] if history else 100
        prev_price = history[-2]['price'] if len(history) > 1 else 100
        change = current_price - prev_price
        
        if change < 0:
            days_to_broke = current_price / abs(change)
            if days_to_broke < 1:
                days_to_broke = 1
            roast_msg = f"📉 If Ayan continues this falling, he will be broke in {int(days_to_broke)} days!"
            report += f"\n🤖 SYSTEM CALCULATION:\n{roast_msg}\n"
        # -----------------------------------------------
        
        # --- DAILY REFLECTION LOG ---
        if ai_data:
            try:
                reflection_path = os.path.join(SCRIPT_DIR, "data", "Daily_Reflection.md")
                with open(reflection_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n## {target_date_str}\n\n")
                    
                    verdict_text = ai_data.get('ai_verdict', '')
                    if verdict_text:
                        f.write(f"**Verdict**: {verdict_text}\n\n")
                        
                    f.write(f"### Productive ({prod_mins}m)\n")
                    prod_list = ai_data.get('productive_breakdown', [])
                    for item in prod_list[:6]:
                        f.write(f"- {item.get('app', 'Unknown')}: {item.get('minutes', 0)}m\n")
                        
                    f.write(f"\n### Wasted ({wasted_mins}m)\n")
                    wasted_list = ai_data.get('wasted_breakdown', [])
                    for item in wasted_list[:6]:
                        f.write(f"- {item.get('app', 'Unknown')}: {item.get('minutes', 0)}m\n")
                        
                    f.write("\n---\n")
            except Exception as e:
                log.error(f"Failed to write daily reflection: {e}")
        # -----------------------------------------------
        chart_path = generate_progress_chart(history)

        if wa_client:
            print("\n[*] JIT Booting WhatsApp for Daily Summary...")
            try:
                wa_client.start_client()
            except Exception as e:
                log.error(f"WA start_client failed for summary: {e}")

            # Wait for WA readiness
            for i in range(120):
                if wa_client.is_ready():
                    break
                time.sleep(1)

            if wa_client.is_ready():
                try:
                    for num in SUMMARY_WHATSAPP_TARGETS:
                        # Custom override for specific contact
                        target_report = report
                        if config.AI_ROAST_OVERRIDE_TARGET and num == config.AI_ROAST_OVERRIDE_TARGET and roast_msg:
                            if config.AI_ROAST_OVERRIDE:
                                target_report = target_report.replace(roast_msg, config.AI_ROAST_OVERRIDE)
                        success = wa_client.send_summary_msg(num, target_report, image_path=chart_path)
                        if not success:
                            queue_failed_message(target_report, "whatsapp", num, image_path=chart_path)
                    print("[+] Daily summary sent via WhatsApp!")
                except Exception as e:
                    log.error(f"WA summary send crash: {e}")
                    for num in SUMMARY_WHATSAPP_TARGETS:
                        target_report = report
                        if config.AI_ROAST_OVERRIDE_TARGET and num == config.AI_ROAST_OVERRIDE_TARGET and roast_msg:
                            if config.AI_ROAST_OVERRIDE:
                                target_report = target_report.replace(roast_msg, config.AI_ROAST_OVERRIDE)
                        queue_failed_message(target_report, "whatsapp", num, image_path=chart_path)
            else:
                log.error("WhatsApp not ready for daily summary")
                for num in SUMMARY_WHATSAPP_TARGETS:
                    target_report = report
                    if config.AI_ROAST_OVERRIDE_TARGET and num == config.AI_ROAST_OVERRIDE_TARGET and roast_msg:
                        if config.AI_ROAST_OVERRIDE:
                            target_report = target_report.replace(roast_msg, config.AI_ROAST_OVERRIDE)
                    queue_failed_message(target_report, "whatsapp", num, image_path=chart_path)

            # Stop client to save memory overnight
            try:
                print("[*] Waiting 10 seconds for WhatsApp to sync message to your phone...")
                time.sleep(10)
                wa_client.stop_client()
            except Exception:
                pass

        if ig_client:
            print("\n[*] Sending Daily Summary via Instagram...")
            try:
                for user in ALERT_IG_USERNAMES:
                    try:
                        ig_client.send_message(user, report, image_path=chart_path)
                    except Exception:
                        queue_failed_message(report, "instagram", user, image_path=chart_path)
                print("[+] Daily summary sent via Instagram!")
            except Exception as e:
                log.error(f"IG send_message failed for summary: {e}")
                try:
                    subprocess.run(['notify-send', '-u', 'critical', '⚠️ IG SESSION FAILED', 'Your Instagram login expired! Check monitor.log'])
                except Exception:
                    pass

    except Exception as e:
        log.error(f"Failed to send daily summary: {e}")