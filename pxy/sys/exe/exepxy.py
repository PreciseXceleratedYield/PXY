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

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_path):
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
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 29))

# ---------------- MAIN LOOP ----------------
print("\n🚀 INIT: main market loop starting now 📡")

loop_counter = 1

# ---------------- RUN PARENT SCRIPTS ONCE AT START ----------------
parent_scripts = [
    HERE.parent / "systdaypxy.py",
    HERE.parent / "sysvixpxy.py",
    HERE.parent / "sysdashpxy.py",
    HERE / "exeentrpxy.py",
    HERE / "exeexitpxy.py"
]

for s in parent_scripts:
    safe_run(s)

# ---------------- MARKET SUB-LOOP ----------------
while True:
    if in_market_hours():
        live_status("🚀 LOOP: waiting CE/PE trigger 📊")

        for sub_itr in range(1, 31):

            # -------- POSITION FETCH --------
            pos_summary = get_position_summary(client)

            # -------- SAFE PARSING (FINAL FIX) --------
            try:
                ce_qty = int(pos_summary.split("CE")[0])
                pe_qty = int(pos_summary.split("CE")[1].replace("PE", ""))
            except Exception:
                ce_qty, pe_qty = 0, 0

            # -------- LIVE STATUS --------
            live_status(f"📊 Loop#{loop_counter} Sub#{sub_itr} CE:{ce_qty} PE:{pe_qty}")

            # -------- CORE LOGIC (UNCHANGED) --------
            if ce_qty >= 1 and pe_qty >= 1:
                safe_run(HERE / "exeexitpxy.py")

            elif ce_qty == 0 and pe_qty == 0:
                safe_run(HERE / "exeentrpxy.py")

            else:
                safe_run(HERE / "exeexitpxy.py")
                safe_run(HERE / "exeentrpxy.py")

            fancy_pause(3)

        loop_counter += 1

    else:
        print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")

        safe_run(HERE.parent / "sysslefpxy.py")

        fancy_pause(5)

        while not in_market_hours():
            print("⏳ WAIT: market opens at 09:16 IST 📡", end="\r")
            time.sleep(60)

        print("\n🚀 MKT OPEN: resuming main loop now 📈")
