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
sys.path.insert(0, str(HERE))

# ---------------- CLIENT SESSION ----------------
try:
    from runclntpxy import get_session
    client = get_session()
    if not client:
        print("❌ FATAL: Unable to create trading session")
        sys.exit(1)
except Exception as e:
    print(f"❌ Client Init Failed: {e}")
    sys.exit(1)

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_path):
    if not Path(script_path).exists():
        print(f"⚠️ SKIP: script not found -> {script_path}")
        print("━" * 42)
        return
    try:
        # Executes script and preserves terminal colors
        subprocess.run(['python3', str(script_path)], check=True, timeout=35)
    except subprocess.TimeoutExpired:
        print(f"⏱ TIMEOUT: script stuck -> {script_path} ⚠️")
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

def live_status(msg):
    print(f"{datetime.now(ist).strftime('%H:%M:%S')} {msg}", end="\r", flush=True)

def in_market_hours():
    now = datetime.now(ist)
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 29))

# ---------------- MAIN LOOP ----------------
print("\n🚀 INIT: main market loop starting (Direct Mode) 📡")

# RUN PARENT SCRIPTS ONCE AT START
parent_scripts = [
    HERE.parent / "systdaypxy.py",
    HERE.parent / "sysvixpxy.py",
    HERE.parent / "sysdashpxy.py",
    HERE / "exeentrpxy.py",
    HERE / "exeexitpxy.py"
]
for s in parent_scripts:
    safe_run(s)

loop_counter = 1
while True:
    if in_market_hours():
        live_status(f"📊 Loop#{loop_counter} | Executing Entry & Exit...")
        
        # --- REMOVED CE/PE CHECK: RUNNING BOTH EVERY TIME ---
        safe_run(HERE / "exeexitpxy.py")
        safe_run(HERE / "exeentrpxy.py")
        
        # Pause to prevent API spamming
        for i in range(3, 0, -1):
            print(f"⏳ Next cycle in... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
            time.sleep(1)
            
        loop_counter += 1
    else:
        print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
        safe_run(HERE.parent / "sysslefpxy.py")
        while not in_market_hours():
            print("⏳ WAIT: market opens at 09:16 IST 📡", end="\r")
            time.sleep(60)
        print("\n🚀 MKT OPEN: resuming main loop now 📈")


