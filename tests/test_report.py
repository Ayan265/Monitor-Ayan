import sys
import os
import datetime
sys.path.append('/home/linuxayan/Desktop/Monitor_ayan')
from monitor import get_top_time_sinks, get_resort_to_grow_stats, update_streak

def generate_mock_report():
    target_date_str = str(datetime.date.today())
    pc_total_time, mobile_total_time, top_pc_apps, top_mobile_apps, wasted_details = get_top_time_sinks(target_date_str)
    
    rtg = get_resort_to_grow_stats(target_date_str)
    
    report = "📊 *Daily Accountability Audit* 📊\n\n"
    
    diff = 0
    td_score = 0
    streak = update_streak(0) # Mock streak
    
    if rtg and (rtg["today"]["prod"] + rtg["today"]["strug"]) > 0:
        td_score = rtg["today_score"]
        streak = update_streak(td_score)
        yd_score = rtg["yesterday_score"]
        diff = td_score - yd_score
        
        report += "🛑 *VERDICT:* "
        if diff > 0 or td_score >= 80:
            report += "🟢 IMPROVING\n"
        elif diff < 0 or td_score < 50:
            report += "🔴 SLACKING\n"
            report += f"Ayan's focus dropped by {abs(diff)}% today. Hold him accountable!\n\n"
        else:
            report += "🟡 STAGNANT\n"
        
        trend_str = ""
        if (rtg["yesterday"]["prod"] + rtg["yesterday"]["strug"]) > 0:
            if diff > 0:
                trend_str = f" (⬆️ {diff}%)"
            elif diff < 0:
                trend_str = f" (⬇️ {abs(diff)}%)"
                
        report += f"🏆 *FOCUS SCORE: {td_score}%*{trend_str}\n"
        report += f"❌ *Streak Broken.*\n\n"
    else:
        report += "🛑 *VERDICT:* ⚪ NO DATA\n\n"
        report += "🏆 *FOCUS SCORE:* N/A\n\n"
        
    total_time = pc_total_time + mobile_total_time
    total_hours = round(total_time / 3600, 1)
    
    report += "⏱️ *WHERE DID HIS TIME GO?*\n"
    report += f"💻 Total Screen Time: {total_hours} hours\n"
    report += f"✅ Productive Work: 1.0 hours\n"
    report += f"🚨 Wasted Time: 1 mins, 1 secs\n"
    report += f"   📺 Anime/Manga: 1m 1s\n\n"
        
    if top_pc_apps:
        pc_hrs = round(pc_total_time / 3600, 1)
        report += f"💻 *Laptop time : {pc_hrs}hr:*\n"
        for i, (app, secs) in enumerate(top_pc_apps, 1):
            app_mins = secs // 60
            dur_str = f"{round(app_mins / 60, 1)} hrs" if app_mins > 60 else f"{app_mins} mins"
            report += f"{i}. {app} ({dur_str})\n"
        report += "\n"
        
    if top_mobile_apps:
        mobile_hrs = round(mobile_total_time / 3600, 1)
        report += f"📱 *Mobile Time: {mobile_hrs}hr:*\n"
        for i, (app, secs) in enumerate(top_mobile_apps, 1):
            app_mins = secs // 60
            dur_str = f"{round(app_mins / 60, 1)} hrs" if app_mins > 60 else f"{app_mins} mins"
            report += f"{i}. {app} ({dur_str})\n"
        report += "\n"
        
    print(report)

generate_mock_report()
