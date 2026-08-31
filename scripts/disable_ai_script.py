with open('/home/linuxayan/Desktop/Monitor_ayan/monitor.py', 'r') as f:
    content = f.read()

# 1. Disable AI API call
old_ai_call = """        ai_data = None
        if top_pc_apps or top_mobile_apps:
            print("[*] Contacting Gemini AI for time categorization...")
            ai_data = analyze_time_with_ai(top_pc_apps, top_mobile_apps)"""

new_ai_call = """        ai_data = None
        # if top_pc_apps or top_mobile_apps:
        #     print("[*] Contacting Gemini AI for time categorization...")
        #     ai_data = analyze_time_with_ai(top_pc_apps, top_mobile_apps)"""

content = content.replace(old_ai_call, new_ai_call)

# 2. Replace Roast with Calculation
old_roast = """        # --- SLACKER'S ROAST ---
        roast_msg = ""
        if verdict in ["Declined", "Stagnant"] or td_score < 50:
            if ai_data and ai_data.get('wasted_breakdown'):
                roast_msg = ai_data.get('wasted_roast', "You slacked off today. Do better tomorrow.")
                report += f"\\n🤖 JARVIS:\\n{roast_msg}\\n"
        # -----------------------------------------------"""

new_roast = """        # --- SYSTEM CALCULATION ---
        roast_msg = ""
        current_price = history[-1]['price'] if history else 100
        prev_price = history[-2]['price'] if len(history) > 1 else 100
        change = current_price - prev_price
        
        if change < 0:
            days_to_broke = current_price / abs(change)
            if days_to_broke < 1:
                days_to_broke = 1
            roast_msg = f"📉 If Ayan continues this falling, he will be broke in {int(days_to_broke)} days!"
            report += f"\\n🤖 SYSTEM CALCULATION:\\n{roast_msg}\\n"
        # -----------------------------------------------"""

content = content.replace(old_roast, new_roast)

with open('/home/linuxayan/Desktop/Monitor_ayan/monitor.py', 'w') as f:
    f.write(content)
print("Updated monitor.py")
