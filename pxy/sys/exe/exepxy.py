#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, time as dt_time
import pytz
from colorama import init, Fore, Style
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import os

# Ensure outputs are sent to stdout immediately without terminal buffering
sys.stdout.reconfigure(line_buffering=True)

# ✅ SWITCH ADDED
SIMPLE_MODE = True  

# ---------------- INIT ----------------
init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
sys.path.insert(0, str(RUN_DIR))
sys.path.insert(0, str(HERE))

print("🛠️ STEP 1: Dependencies and paths loaded successfully.")

# ---------------- IMPORT POSITION CHECK ----------------
try:
    from runpchkpxy import get_position_summary
    print("✅ STEP 2: Position summary module imported successfully.")
except Exception as e:
    print(f"⚠️ WARN: position summary import failed ({e}) ⚠️")
    get_position_summary = lambda client=None: "0CE0PE"

# ---------------- CREATE CLIENT ONCE (FIXED) ----------------
try:
    from runclntpxy import get_session
    client = get_session()
    if not client:
        print("❌ FATAL: Unable to create trading session")
        sys.exit(1)
    print("✅ STEP 3: Trading API session initialized successfully.")
except Exception as e:
    print(f"❌ Client Init Failed: {e}")
    sys.exit(1)

# ---------------- API TIMEOUT WRAPPER ----------------
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
        return
    try:
        actual_timeout = 30 if timeout is None else timeout
        print(f"🔄 Executing sub-script: {Path(script_path).name}")
        subprocess.run(['python3', str(script_path)], check=True, timeout=actual_timeout)
    except subprocess.TimeoutExpired:
        print(f"⏱ TIMEOUT: script finished execution limit -> {script_path} ⚠️")
    except subprocess.CalledProcessError:
        print(f"❌ RUN ERR: script execution failed -> {script_path} ⚠️")
    except Exception as e:
        print(f"❌ RUN ERR: unexpected failure -> {script_path} ⚠️")

def safe_run(script_path, timeout=20):
    try:
        run_script(script_path, timeout=timeout)
    except Exception:
        print("⚠️ SAFE RUN: unexpected error occurred ⚠️")

def fancy_pause(seconds=7):
    for i in range(seconds, 0, -1):
        print(f"⏳ Pause active... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
        time.sleep(1)
    print("✅ Resume execution now ")

def live_status(msg):
    print(f"[{datetime.now(ist).strftime('%H:%M:%S')}] {msg}")

def in_market_hours():
    now = datetime.now(ist)
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 29))

# ---------------- MAIN INITIALIZATION ----------------
print("\n🚀 INIT: Verifying pre-flight parent scripts...")
parent_scripts = [
    HERE.parent / "systdaypxy.py",
    HERE.parent / "sysvixpxy.py",
    HERE.parent / "sysdashpxy.py",
    HERE / "exeentrpxy.py",
    HERE / "exernkopxy.py",
    HERE / "exeexitpxy.py"
]

for s in parent_scripts:
    print(f"📦 checking component: {s.name}")
    safe_run(s, timeout=20)

print("\n📡 Entering primary monitoring engine sequence loop...")

# ---------------- ENGINE LOOP ----------------
while True:
    if in_market_hours():
        live_status("🚀 LOOP: Live market window detected.")
        
        for sub_itr in range(1, 31):
            pos_summary = call_with_timeout(get_position_summary, 7, client)
            if not pos_summary:
                pos_summary = "0CE0PE"
            
            try:
                # FIXED: Corrected structural list unpack logic to prevent continuous silent loops
                parts = pos_summary.split("CE")
                ce_qty = int(parts[0])
                pe_qty = int(parts[1].replace("PE", ""))
            except Exception:
                ce_qty, pe_qty = 0, 0
                
            print(f"📊 Loop Sub#{sub_itr} | Active Positions -> CE:{ce_qty} PE:{pe_qty}")
            
            if SIMPLE_MODE:
                safe_run(HERE / "exernkopxy.py", timeout=30)
                safe_run(HERE / "exeexitpxy.py", timeout=20)
                safe_run(HERE / "exeentrpxy.py", timeout=20)
            else:
                if ce_qty > 0 and ce_qty == pe_qty:
                    safe_run(HERE / "exeexitpxy.py", timeout=20)
                elif ce_qty == 0 and pe_qty == 0:
                    safe_run(HERE / "exeentrpxy.py", timeout=20)
                else:
                    safe_run(HERE / "exeexitpxy.py", timeout=20)
                    safe_run(HERE / "exeentrpxy.py", timeout=20)
                    
            fancy_pause(7)
    else:
        # VISUAL FIX: Print status continuously when market is closed to confirm it is running
        live_status("🌙 MARKET CLOSED: Running off-hour routines...")
        safe_run(HERE.parent / "sysslefpxy.py", timeout=20)
        
        print("⏳ Entering overnight sleep watch routine...")
        while not in_market_hours():
            safe_run(HERE.parent / "syscprtpxy.py", timeout=20)
            # Force printing out to confirm engine is alive
            print(f"💤 [{datetime.now(ist).strftime('%H:%M:%S')}] Standby Mode: Waiting for market opening (09:16 IST)...")
            time.sleep(15)
