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

# ---------------- CONFIG & TIMINGS ----------------
init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")
MARKET_START = dt_time(9, 16)
MARKET_END = dt_time(15, 29)

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
sys.path.extend([str(RUN_DIR), str(HERE)])

# ---------------- DEPLOY DEPENDENCIES ----------------
try:
    from runpchkpxy import get_position_summary
except Exception:
    print("⚠️ WARN: position summary import failed ⚠️")
    get_position_summary = lambda client=None: "0CE0PE"

try:
    from runclntpxy import get_session
    client = get_session()
    if not client:
        print("❌ FATAL: Unable to create trading session")
        sys.exit(1)
except Exception as e:
    print(f"❌ Client Init Failed: {e}")
    sys.exit(1)

# ---------------- EXECUTION ENGINE ----------------
def call_with_timeout(func, timeout=7, *args, **kwargs):
    """Executes target functions with an explicit safety timeout window."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            print("⏱ API TIMEOUT: position fetch took too long ⚠️")
        except Exception as e:
            print(f"❌ API ERROR: {e}")
        return None

def run_script(script_path, timeout=20):
    """Core process wrapper managing sub-module script executions."""
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

def fancy_pause(seconds=7):
    """Clean operational interface timer delay layout."""
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

# Optimization: Deduplicated scripts dynamically managed using an unrolled loop array
parent_scripts = [
    (HERE.parent / "systdaypxy.py", 20),
    (HERE.parent / "sysvixpxy.py", 20),
    (HERE.parent / "sysdashpxy.py", 20),
    (HERE / "exeentrpxy.py", 20),
    (HERE / "exernkopxy.py", None),  # Infinite runtime allocation
    (HERE / "exeexitpxy.py", 20)
]

for script, tout in parent_scripts:
    run_script(script, timeout=tout)

# ---------------- MAIN RUNTIME ENGINE ----------------
loop_counter = 1

while True:
    os.system('clear')
    
    if in_market_hours():
        print(f"{datetime.now(ist).strftime('%H:%M:%S')} 🚀 LOOP: waiting trigger 📊", end="\r", flush=True)
        
        for sub_itr in range(1, 31):
            pos_summary = call_with_timeout(get_position_summary, 7, client) or "0CE0PE"
            
            # Optimization: Optimized parsing logic using string partitioning to prevent index crashes
            try:
                ce_part, _, pe_part = pos_summary.partition("CE")
                ce_qty = int(ce_part)
                pe_qty = int(pe_part.replace("PE", ""))
            except Exception:
                ce_qty, pe_qty = 0, 0
                
            os.system('clear')
            print(f"📊 Loop#{loop_counter} Sub#{sub_itr} CE:{ce_qty} PE:{pe_qty}")
            
            # 1. Exit management runs on every iteration
            run_script(HERE / "exeexitpxy.py", timeout=20)
            
            # 2. Strategy entry conditions validated dynamically
            if ce_qty == 0 or pe_qty == 0:
                run_script(HERE / "exeentrpxy.py", timeout=20)
            else:
                print(f"{Fore.YELLOW}⏳ Entry skipped - CE ({ce_qty}) 🚧  🚧 PE ({pe_qty})")
                    
            fancy_pause(7)
            
        loop_counter += 1
    else:
        print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
        run_script(HERE.parent / "sysslefpxy.py", timeout=20)
        fancy_pause(7)
        
        while not in_market_hours():
            os.system('clear')
            # Optimization: Eliminated identical duplicate lines that ran syscprtpxy twice consecutively
            run_script(HERE.parent / "syscprtpxy.py", timeout=20)
            print(" ⏳   WAIT : market opens at 09:16 IST  📡", end="\r")
            time.sleep(60)

        print("\n🚀 MKT OPEN: resuming main loop now 📈")

