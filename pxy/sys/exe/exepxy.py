#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, time as dt_time
import pytz
from colorama import init, Fore, Style
import sys
from pathlib import Path
import os  # ✅ Kept for screen clearing

# ---------------- INIT ----------------
init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
SYS_DIR = HERE.parent
for path in (RUN_DIR, HERE, SYS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from syscnfgpxy import RUNMODE

if __name__ == "__main__" and RUNMODE == "SIM":
    from syssimpxy import main as run_simulation

    raise SystemExit(run_simulation())

from sysmodepxy import dispatch_mode

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_path, timeout=None):
    if not Path(script_path).exists():
        print(f"⚠️ SKIP: script not found -> {script_path}")
        print("━" * 42)
        return
    try:
        # ✅ Dynamic timeout value is passed here (None means run forever)
        subprocess.run(['python3', str(script_path)], check=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"⏱ TIMEOUT: script stuck after {timeout}s -> {script_path} ⚠️")
    except subprocess.CalledProcessError:
        print(f"❌ RUN ERR: script execution failed -> {script_path} ⚠️")
    except Exception as e:
        print(f"❌ RUN ERR: unexpected failure -> {script_path} ⚠️")
    print("━" * 42)

def safe_run(script_path, timeout=None):
    try:
        run_script(script_path, timeout=timeout)
    except Exception:
        print("⚠️ SAFE RUN: unexpected error occurred ⚠️")

# UPDATED: Default pause set to 7 seconds
def fancy_pause(seconds=7):
    for i in range(seconds, 0, -1):
        print(f"⏳ Pause active... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
        time.sleep(1)
    print("✅ Resume execution now ")

def live_status(msg):
    print(f"{datetime.now(ist).strftime('%H:%M:%S')} {msg}", end="\r", flush=True)

def _in_market_hours_production():
    now = datetime.now(ist)
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 29))


def in_market_hours():
    return dispatch_mode("engine_window_open", _in_market_hours_production)

# ---------------- MAIN LOOP ----------------
os.system('clear')  # ✅ Initial screen clear
print("\n🚀 INIT: main market loop starting now [SIMPLE MODE ONLY] 📡")
loop_counter = 1

# Initial system check scripts
parent_scripts = [
    HERE.parent / "sysdashpxy.py",
    HERE / "exeentrpxy.py",
    HERE / "exeexitpxy.py"
]

if dispatch_mode("run_startup_checks", lambda: True):
    for s in parent_scripts:
        safe_run(s)
else:
    print("CHK MODE: engine startup checks paused during market hours.")

while True:
    os.system('clear')  # ✅ Clears Ubuntu screen at the start of every main loop iteration
    
    if in_market_hours():
        live_status("🚀 LOOP: waiting trigger 📊")
        
        for sub_itr in range(1, 31):
            os.system('clear')  # ✅ Clears screen before printing the loop iteration index
            print(f"📊 Loop#{loop_counter} Sub#{sub_itr} | Execution Stack Running...")
            
            # -------- REARRANGED RE-ORDERED CORE EXECUTION STACK --------
            safe_run(HERE / "exeexitpxy.py", timeout=60)    # 1️⃣ Clean target exit evaluation (Locks profits first)
            safe_run(HERE / "exeentrpxy.py", timeout=60)    # 2️⃣ Entry generation script (Deploys new layout)
            safe_run(HERE / "exeavgpxy.py", timeout=60)    # 3️⃣ Balancing / Averaging Engine (Runs adjustments last)
                    
            fancy_pause(4)  # 7-second pause between sub-iterations
            
        loop_counter += 1
    else:
        if dispatch_mode("run_closed_market_tasks", lambda: True):
            print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
            safe_run(HERE.parent / "sysslefpxy.py")
        else:
            print("\nCHK MODE: engine paused during market hours.")
        fancy_pause(7)
        
        while not in_market_hours():
            os.system('clear')  # ✅ Clears screen while waiting overnight so logs don't stack up
            if dispatch_mode("run_closed_market_tasks", lambda: True):
                safe_run(HERE.parent / "syscprtpxy.py")
                print(" ⏳   WAIT : market opens at 09:16 IST  📡", end="\r")
            else:
                print(" ⏳   CHK waits until market close  📡", end="\r")
            time.sleep(60)

        print("\n🚀 MKT OPEN: resuming main loop now 📈")
