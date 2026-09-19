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
sys.path.insert(0, str(RUN_DIR))
sys.path.insert(0, str(HERE))

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_path, timeout=45):
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

def safe_run(script_path, timeout=45):
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

def in_market_hours():
    now = datetime.now(ist)
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 29))

# ---------------- MAIN LOOP ----------------
os.system('clear')  # ✅ Initial screen clear
print("\n🚀 INIT: main market loop starting now [SIMPLE MODE ONLY] 📡")
loop_counter = 1

# Initial system check scripts
parent_scripts = [
    HERE.parent / "systdaypxy.py",
    HERE.parent / "sysvixpxy.py",
    HERE.parent / "sysdashpxy.py",
    HERE / "exeentrpxy.py",
    HERE / "exernkopxy.py",
    HERE / "exeexitpxy.py"
]

# Run parent scripts with the exception applied
for s in parent_scripts:
    if s.name == "exernkopxy.py":
        safe_run(s, timeout=None)  # Infinite exception
    else:
        safe_run(s, timeout=45)  # Standard limit

while True:
    os.system('clear')  # ✅ Clears Ubuntu screen at the start of every main loop iteration
    
    if in_market_hours():
        live_status("🚀 LOOP: waiting trigger 📊")
        
        for sub_itr in range(1, 31):
            os.system('clear')  # ✅ Clears screen before printing the loop iteration index
            print(f"📊 Loop#{loop_counter} Sub#{sub_itr} | Execution Stack Running...")
            
            # -------- REARRANGED RE-ORDERED CORE EXECUTION STACK --------
            safe_run(HERE / "exernkopxy.py", timeout=None)  # 1️⃣ Infinite exception
            safe_run(HERE / "exeexitpxy.py", timeout=45)    # 2️⃣ Clean target exit evaluation (Locks profits first)
            safe_run(HERE / "exeentrpxy.py", timeout=45)    # 3️⃣ Entry generation script (Deploys new layout)
            safe_run(HERE / "exeenexpxy.py", timeout=45)    # 4️⃣ Balancing / Averaging Engine (Runs adjustments last)
                    
            fancy_pause(4)  # 7-second pause between sub-iterations
            
        loop_counter += 1
    else:
        print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
        safe_run(HERE.parent / "sysslefpxy.py", timeout=45)
        fancy_pause(7)
        
        while not in_market_hours():
            os.system('clear')  # ✅ Clears screen while waiting overnight so logs don't stack up
            safe_run(HERE.parent / "syscprtpxy.py")  # Fixed: Duplicate entry removed here
            print(" ⏳   WAIT : market opens at 09:16 IST  📡", end="\r")
            time.sleep(60)

        print("\n🚀 MKT OPEN: resuming main loop now 📈")
