import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from monitor import get_resort_to_grow_stats, get_top_time_sinks, get_streak, update_streak, load_stats

def mock_update_streak(score):
    return get_streak()

def get_report():
    import monitor
    monitor.update_streak = mock_update_streak # don't modify disk
    time_spent, alert_sent, saved_date = load_stats()
    
    target_date_str = None
    rtg = get_resort_to_grow_stats(target_date_str)
    
    report = "🚨 *AYAN'S DAILY ACCOUNTABILITY AUDIT* 🚨\n\n"
    
    if target_date_str:
        report += f"*(Recovery Summary for {target_date_str})*\n\n"
        
    diff = 0
    td_score = 0
    if rtg and (rtg["today"]["prod"] + rtg["today"]["strug"]) > 0:
        td_score = rtg["today_score"]
        streak = mock_update_streak(td_score)
        yd_score = rtg["yesterday_score"]
        diff = td_score - yd_score
        
        report += "🛑 *VERDICT:* "
        if diff > 0 or td_score >= 80:
            report += "🟢 IMPROVING\n"
            if streak > 0:
                report += "Ayan is successfully progressing each day.\n\n"
            else:
                report += "Ayan progressed today much better.\n\n"
        elif diff < 0 or td_score < 50:
            report += "🔴 SLACKING\n"
            report += f"Ayan's focus dropped by {abs(diff)}% today. Hold him accountable!\n\n"
        else:
            report += "🟡 STAGNANT\n"
            report += "Ayan had a mediocre day. Push him to do better.\n\n"
        
        trend_str = ""
        if (rtg["yesterday"]["prod"] + rtg["yesterday"]["strug"]) > 0:
            if diff > 0:
                trend_str = f" (⬆️ {diff}%)"
            elif diff < 0:
                trend_str = f" (⬇️ {abs(diff)}%)"
                
        report += f"🏆 *FOCUS SCORE: {td_score}%*{trend_str}\n"
        
        if streak > 0:
            report += f"🔥 *{streak}-Day Focus Streak!*\n\n"
        else:
            report += f"❌ *Streak Broken.*\n\n"
    else:
        report += "🛑 *VERDICT:* ⚪ NO DATA\nAyan didn't track his habits today.\n\n"
        report += "🏆 *FOCUS SCORE:* N/A\n\n"
        
    pc_total_time, mobile_total_time, top_pc_apps, top_mobile_apps, wasted_details = get_top_time_sinks(target_date_str)
    total_time = pc_total_time + mobile_total_time
    top_apps = top_pc_apps  # Use PC apps for display
    total_hours = round(total_time / 3600, 1)
    
    prod_mins = (time_spent.get('coding', 0) + time_spent.get('research', 0)) // 60
    prod_hours = round(prod_mins / 60, 1)
    
    report += "⏱️ *WHERE DID HIS TIME GO?*\n"
    report += f"📱 Total Screen Time: {total_hours} hours\n"
    report += f"✅ Productive Work: {prod_hours} hours\n"
    
    bad_secs = time_spent.get('bad_habit', 0)
    if bad_secs == 0:
        report += f"🚨 Wasted Time: 0 seconds (Perfect)\n\n"
    else:
        report += f"🚨 Wasted Time: {bad_secs} seconds\n\n"
        
    if top_apps:
        report += "🔝 *Top 6 Window Sinks:*\n"
        for i, (app, secs) in enumerate(top_apps, 1):
            app_mins = secs // 60
            if app_mins > 60:
                dur_str = f"{round(app_mins / 60, 1)} hrs"
            else:
                dur_str = f"{app_mins} mins"
            report += f"{i}. {app} ({dur_str})\n"
        report += "\n"
        
    if diff < 0 or td_score < 50:
        report += "Keep him in check."
    else:
        report += "Encourage him! 🔥"

    print(report)

if __name__ == "__main__":
    get_report()
