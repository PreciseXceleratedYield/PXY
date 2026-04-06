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
def run_script(script_path):
    """Run a python script safely."""
    if not Path(script_path).exists():
        print(f"⚠️ SKIP: script not found -> {script_path}")
        print("━" * 42)
        return
    try:
        subprocess.run(['python3', script_path], check=True)
    except subprocess.CalledProcessError:
        print(f"❌ RUN ERR: script execution failed -> {script_path} ⚠️")
    except Exception as e:
        print(f"❌ RUN ERR: unexpected failure -> {script_path} ⚠️")
    print("━" * 42)

def safe_run(script_path):
    try:
        run_script(script_path)
    except Exception:
        print("⚠️ SAFE RUN: unexpected error occurred ⚠️")
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
parent_scripts = [
    HERE.parent / "systdaypxy.py",    # parent directory
    HERE.parent / "sysvixpxy.py",
    HERE.parent / "sysdashpxy.py",
    HERE / "exeentrpxy.py",           # current directory
    HERE / "exeexitpxy.py"
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
            try:
                ce_qty = int(pos_summary[0])
                pe_qty = int(pos_summary[3])
            except Exception:
                ce_qty = 0
                pe_qty = 0

            live_status(f"📊 Loop#{loop_counter} Sub#{sub_itr} CE:{ce_qty} PE:{pe_qty}")

            if ce_qty >= 1 and pe_qty >= 1:
                safe_run(HERE / "exeexitpxy.py")
            elif ce_qty == 0 and pe_qty == 0:
                safe_run(HERE / "exeentrpxy.py")
            else:
                safe_run(HERE / "exeentrpxy.py")
                safe_run(HERE / "exeexitpxy.py")

            fancy_pause(3)

        loop_counter += 1

    else:
        print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
        
        # Cleanup script in parent directory
        safe_run(HERE.parent / "sysslefpxy.py")
        
        fancy_pause(5)
        
        # Wait until next market open
        while not in_market_hours():
            print("⏳ WAIT: market opens at 09:16 IST 📡", end="\r")
            time.sleep(60)
        print("\n🚀 MKT OPEN: resuming main loop now 📈")
