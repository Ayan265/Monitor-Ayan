import subprocess, time, threading

timeout_seconds = 10
prompt_text = "What did you do in the last 20 minutes?\n\nTop Apps (Since last prompt):\n1. Firefox (10m)\n2. Terminal (5m)"
print("[*] Launching prompt...")

player_proc = None
try:
    player_proc = subprocess.Popen(
        ["ffplay", "-nodisp", "-autoexit", "/home/linuxayan/Desktop/lose.mp3"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
except Exception as e:
    print(f"Failed to play music: {e}")

keep_focus = True
def force_focus():
    while keep_focus:
        try:
            subprocess.run(["xdotool", "search", "--name", "Accountability Check", "windowactivate"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except:
            pass
        time.sleep(1)
threading.Thread(target=force_focus, daemon=True).start()

result = subprocess.run(
    [
        "zenity", 
        "--entry", 
        "--title=Accountability Check", 
        "--text=" + prompt_text, 
        f"--timeout={timeout_seconds}"
    ],
    capture_output=True,
    text=True
)

keep_focus = False # Stop focus thread
if player_proc:
    try:
        player_proc.terminate()
    except:
        pass
        
print("Result:", result.returncode, "stdout:", result.stdout.strip())
