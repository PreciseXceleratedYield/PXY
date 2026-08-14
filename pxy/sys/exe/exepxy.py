#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, time as dt_time
import pytz
from colorama import init, Fore, Style
import sys
from pathlib import Path
import os

# ---------------- CONFIG & TIMINGS ----------------
init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")
MARKET_START = dt_time(9, 16)
MARKET_END = dt_time(15, 29)

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
sys.path.extend([str(RUN_DIR), str(HERE)])

# ---------------- EXECUTION ENGINE ----------------
def run_script(script_path, timeout=30):
    """Core process wrapper managing sub-module script executions with a 30s timeout."""
    if not Path(script_path).exists():
        print(f"⚠️ SKIP: script not found -> {script_path}\n" + "━" * 42)
        return
    try:
        subprocess.run(['python3', str(script_path)], check=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"⏱ TIMEOUT: script stuck after {timeout}s -> {script_path} ⚠️")
    except subprocess.CalledProcessError:
        print(f"❌ RUN ERR: script execution failed -> {script_path} ⚠️")
    except Exception as e:
        print(f"❌ RUN ERR: unexpected failure -> {script_path} ⚠️")
    print("━" * 42)

def fancy_pause(seconds=30):
    """Clean operational interface timer delay layout adjusted to 30s."""
    for i in range(seconds, 0, -1):
        print(f"⏳ Pause active... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
        time.sleep(1)
    print("✅ Resume execution now ")

def in_market_hours():
    """True if active day is weekday and current time falls inside market bounds."""
    now = datetime.now(ist)
    return 0 <= now.weekday() <= 4 and MARKET_START <= now.time() <= MARKET_END

# ---------------- INITIALIZATION CHECK ----------------
os.system('clear')
print("\n🚀 INIT: main market loop starting now 📡")

# System startup routines (Configured with 30s timeouts where applicable)
parent_scripts = [
    (HERE.parent / "systdaypxy.py", 30),
    (HERE.parent / "sysvixpxy.py", 30),
    (HERE.parent / "sysdashpxy.py", 30),
    (HERE / "exernkopxy.py", None)  # Infinite runtime allocation
]

for script, tout in parent_scripts:
    run_script(script, timeout=tout)

# ---------------- MAIN RUNTIME ENGINE ----------------
loop_counter = 1

while True:
    os.system('clear')
    
    if in_market_hours():
        print(f"🔄 Loop #{loop_counter} | {datetime.now(ist).strftime('%H:%M:%S')} 🚀 Running execution pipeline...")
        print("━" * 42)
        
        # 1. Unconditional exit management execution (30s timeout restriction)
        print("➡️ Executing Exit Management...")
        run_script(HERE / "exeexitpxy.py", timeout=30)
        
        # 2. Unconditional strategy entry execution (30s timeout restriction)
        print("➡️ Executing Entry Strategy...")
        run_script(HERE / "exeentrpxy.py", timeout=30)
            
        # Updated cooldown window to 30 seconds
        fancy_pause(6)
        loop_counter += 1
        
    else:
        print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
        run_script(HERE.parent / "sysslefpxy.py", timeout=30)
        fancy_pause(30)
        
        while not in_market_hours():
            os.system('clear')
            run_script(HERE.parent / "syscprtpxy.py", timeout=30)
            print(" ⏳   WAIT : market opens at 09:16 IST  📡", end="\r")
            time.sleep(6)

        print("\n🚀 MKT OPEN: resuming main loop now 📈")

