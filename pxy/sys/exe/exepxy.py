#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, time as dt_time
import pytz
from colorama import init, Fore, Style
import sys
from pathlib import Path

# ---------------- INIT ----------------
init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
sys.path.insert(0, str(RUN_DIR))  # run subdir for runpchkpxy
sys.path.insert(0, str(HERE))     # current exe dir

# ---------------- IMPORT POSITION CHECK ----------------
try:
    from runpchkpxy import get_position_summary
except Exception as e:
    print(f"[WARN] Cannot import get_position_summary: {e}")
    get_position_summary = lambda: "0CE0PE"

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_name):
    try:
        subprocess.run(['python3', script_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"\033[91mError in {script_name}: {e}\033[0m")
    except Exception as e:
        print(f"\033[91mUnexpected error in {script_name}: {e}\033[0m")
    print("━" * 42)

def safe_run(script_name):
    try:
        run_script(script_name)
    except Exception as e:
        print(f"⚠️ Script {script_name} failed: {e}")
        import traceback
        traceback.print_exc()

def fancy_pause(seconds=3):
    for i in range(seconds, 0, -1):
        print(f"⏳ Pausing... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
        time.sleep(1)
    print("✅ Resuming execution!        ")

def live_status(msg):
    print(f"{datetime.now(ist).strftime('%H:%M:%S')} {msg}", end="\r", flush=True)

def in_market_hours():
    now = datetime.now(ist)
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 25))

# ---------------- MAIN LOOP ----------------
print("\n⏳ Starting main market loop...")

loop_counter = 1

# ---------------- RUN PARENT SCRIPTS ONCE AT START ----------------
# ---------------- RUN PARENT AND LOCAL EXE SCRIPTS ----------------
parent_scripts = [
    str(HERE.parent / "systdaypxy.py"),   # parent directory
    str(HERE.parent / "sysvixpxy.py"),
    str(HERE.parent / "sysdashpxy.py"),
    str(HERE / "exeentrpxy.py"),          # current/exe directory
    str(HERE / "exeexitpxy.py")
]

for s in parent_scripts:
    safe_run(s)

# ---------------- MARKET SUB-LOOP ----------------
while True:
    if in_market_hours():
        live_status(f"⏳ Main loop active. Waiting for CE/PE subloop...")

        # 30-iteration subloop
        for sub_itr in range(1, 31):
            pos_summary = get_position_summary()
            ce_qty = int(pos_summary[0])
            pe_qty = int(pos_summary[3])

            live_status(f"Loop #{loop_counter} | Subloop #{sub_itr} | CE:{ce_qty} PE:{pe_qty}")

            if ce_qty >= 1 and pe_qty >= 1:
                safe_run("exeexitpxy.py")
            elif ce_qty == 0 and pe_qty == 0:
                safe_run("exeentrpxy.py")
            else:
                safe_run("exeentrpxy.py")
                safe_run("exeexitpxy.py")

            fancy_pause(3)

        loop_counter += 1

    else:
        print("\n💤 Market closed → end-of-day cleanup")
        safe_run(str(HERE / "sysslefpxy.py"))  # full path ensures correct file
        fancy_pause(5)
    
        # Wait until next market open
        while not in_market_hours():
            print("⏳ Waiting for market to open (9:16 IST)", end="\r")
            time.sleep(60)
        print("\n⏳ Market opened! Resuming main loop...")
