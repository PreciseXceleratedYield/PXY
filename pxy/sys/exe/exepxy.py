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
    print("⚠️ WARN: position summary import failed ⚠️")
    get_position_summary = lambda: "0CE0PE"

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_name):
    try:
        subprocess.run(['python3', script_name], check=True)
    except subprocess.CalledProcessError as e:
        print("❌ RUN ERR: script execution failed ⚠️")
    except Exception as e:
        print("❌ RUN ERR: unexpected failure occurred ⚠️")
    print("━" * 42)

def safe_run(script_name):
    try:
        run_script(script_name)
    except Exception as e:
        print("⚠️ SAFE RUN: script execution failed ⚠️")
        import traceback
        traceback.print_exc()

def fancy_pause(seconds=3):
    for i in range(seconds, 0, -1):
        print(f"⏳ Pause active... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
        time.sleep(1)
    print("✅ Resume execution now        ")

def live_status(msg):
    print(f"{datetime.now(ist).strftime('%H:%M:%S')} {msg}", end="\r", flush=True)

def in_market_hours():
    now = datetime.now(ist)
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 25))

# ---------------- MAIN LOOP ----------------
print("\n🚀 INIT: main market loop starting now 📡")

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
        live_status("🚀 LOOP ACTIVE: waiting CE/PE trigger 📊")

        # 30-iteration subloop
        for sub_itr in range(1, 31):
            pos_summary = get_position_summary()
            ce_qty = int(pos_summary[0])
            pe_qty = int(pos_summary[3])

            live_status(f"📊 Loop#{loop_counter} Sub#{sub_itr} CE:{ce_qty} PE:{pe_qty}")

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
        print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
        
        # Correct full path to parent sys folder
        safe_run(str(HERE.parent / "sysslefpxy.py"))
        
        fancy_pause(5)
    
        # Wait until next market open
        while not in_market_hours():
            print("⏳ WAIT: market opens at 09:16 IST 📡", end="\r")
            time.sleep(60)
        print("\n🚀 MKT OPEN: resuming main loop now 📈")
