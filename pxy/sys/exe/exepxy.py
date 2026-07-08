#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, time as dt_time
import pytz
from colorama import init, Fore, Style
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import os  # ✅ Added for screen clearing

# ✅ SWITCH ADDED
SIMPLE_MODE = True  # Set to True to remove CE/PE check and run both scripts every loop

# ---------------- INIT ----------------
init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
sys.path.insert(0, str(RUN_DIR))
sys.path.insert(0, str(HERE))

# ---------------- IMPORT POSITION CHECK ----------------
try:
    from runpchkpxy import get_position_summary
except Exception:
    print("⚠️ WARN: position summary import failed ⚠️")
    get_position_summary = lambda client=None: "0CE0PE"

# ---------------- CREATE CLIENT ONCE (FIXED) ----------------
try:
    from runclntpxy import get_session
    client = get_session()
    if not client:
        print("❌ FATAL: Unable to create trading session")
        sys.exit(1)
except Exception as e:
    print(f"❌ Client Init Failed: {e}")
    sys.exit(1)

# ---------------- FIX 2: API TIMEOUT WRAPPER ----------------
def call_with_timeout(func, timeout=10, *args, **kwargs):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            print("⏱ API TIMEOUT: position fetch took too long ⚠️")
            return None
        except Exception as e:
            print(f"❌ API ERROR: {e}")
            return None

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_path, timeout=20):
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

def safe_run(script_path, timeout=20):
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
print("\n🚀 INIT: main market loop starting now 📡")
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
        safe_run(s, timeout=20)  # Standard limit

while True:
    os.system('clear')  # ✅ Clears Ubuntu screen at the start of every main loop iteration
    
    if in_market_hours():
        live_status("🚀 LOOP: waiting trigger 📊")
        
        for sub_itr in range(1, 31):
            # API call with 7s timeout
            pos_summary = call_with_timeout(get_position_summary, 7, client)
            if not pos_summary:
                pos_summary = "0CE0PE"
            
            try:
                ce_qty = int(pos_summary.split("CE")[0])
                pe_qty = int(pos_summary.split("CE")[1].replace("PE", ""))
            except Exception:
                ce_qty, pe_qty = 0, 0
                
            os.system('clear')  # ✅ Clears screen before printing the updated live loop status
            print(f"📊 Loop#{loop_counter} Sub#{sub_itr} CE:{ce_qty} PE:{pe_qty}")
            
            # -------- CORE LOGIC WITH SWITCH --------
            if SIMPLE_MODE:
                safe_run(HERE / "exernkopxy.py", timeout=None)  # Infinite exception
                safe_run(HERE / "exeexitpxy.py", timeout=20)
                #safe_run(HERE.parent / "sysrigpxy.py", timeout=20)
                safe_run(HERE / "exeentrpxy.py", timeout=20)
            else:
                if ce_qty > 0 and ce_qty == pe_qty:
                    safe_run(HERE / "exeexitpxy.py", timeout=20)
                elif ce_qty == 0 and pe_qty == 0:
                    safe_run(HERE / "exeentrpxy.py", timeout=20)
                else:
                    safe_run(HERE / "exeexitpxy.py", timeout=20)
                    safe_run(HERE / "exeentrpxy.py", timeout=20)
                    
            fancy_pause(7)  # 7-second pause between sub-iterations
            
        loop_counter += 1
    else:
        print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
        safe_run(HERE.parent / "sysslefpxy.py", timeout=20)
        fancy_pause(7)
        
        while not in_market_hours():
            os.system('clear')  # ✅ Clears screen while waiting overnight so logs don't stack up
            safe_run(HERE.parent / "syscprtpxy.py")
            safe_run(HERE.parent / "syscprtpxy.py")
            print(" ⏳   WAIT : market opens at 09:16 IST  📡", end="\r")
            time.sleep(60)

        print("\n🚀 MKT OPEN: resuming main loop now 📈")


