# _sys.py
#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime, time as dt_time
import pytz
from colorama import init, Fore, Style
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError

# =====================================================================
# SYSTEM CORE FLAGS & CONFIGURATION
# =====================================================================
SIMPLE_MODE = True  # Strict operational switch: sequential execution
DEBUG_MODE = False
LOOP_INTERVAL = 7   # 7-second cooldown pause matching timeout

init(autoreset=True)
ist = pytz.timezone("Asia/Kolkata")
HERE = Path(__file__).resolve().parent

# --- INTEGRATED POSITION SUMMARY READ ENGINE (FLAT IMPORT) ---
from _entry import get_global_position_summary

# --- INITIALIZE SHARED BROKER CLIENT ONCE AT BOOT ---
try:
    from _clnt import get_session
    client = get_session()
    if not client:
        print(f"{Fore.RED}❌ FATAL: Unable to instantiate shared trading session connection profile.")
        sys.exit(1)
    print(f"{Fore.GREEN}✅ SESSION INITIALIZATION SUCCESS: Shared client channel live.")
except Exception as e:
    print(f"{Fore.RED}❌ Client Init Failed: {e}")
    sys.exit(1)

# =====================================================================
# API TIMEOUT PROTECTION THREAD WRAPPER
# =====================================================================
def call_with_timeout(func, timeout=7, *args, **kwargs):
    """Wraps broker API commands inside a concurrent isolated worker thread."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            print(f"\n{Fore.YELLOW}⏱ API TIMEOUT: Broker position request exceeded {timeout}s wall limit. ⚠️")
            return None
        except Exception as e:
            print(f"\n{Fore.RED}❌ API ERROR: Position call failure -> {e}")
            return None

# =====================================================================
# CONTROLLED SUBPROCESS SCRIPT EXECUTION ENGINE (FLAT PATH)
# =====================================================================
def run_script(script_name):
    """Executes target script residing flatly in the same directory."""
    script_path = HERE / script_name
    if not script_path.exists():
        if DEBUG_MODE: print(f"{Fore.YELLOW}⚠️ SKIP: target flat asset script not found -> {script_name}")
        return
    try:
        subprocess.run(['python3', str(script_path)], check=True, timeout=20)
    except subprocess.TimeoutExpired:
        print(f"{Fore.RED}⏱ TIMEOUT: Subprocess execution frozen -> {script_name} ⚠️")
    except subprocess.CalledProcessError:
        print(f"{Fore.RED}❌ RUN ERR: Subprocess returned error exit code -> {script_name} ⚠️")
    except Exception as e:
        print(f"{Fore.RED}❌ RUN ERR: Unexpected error executing -> {script_name} | {e} ⚠️")

def fancy_pause(seconds=7):
    """Enforces clean countdown timer inside terminal line buffer."""
    for i in range(seconds, 0, -1):
        print(f"⏳ Cooldown active... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
        time.sleep(1)
    print("✅ System ready for next iteration ")

# =====================================================================
# FIXED SYNTAX BUG LINE: Cleaned the string format syntax token safely
# =====================================================================
def live_status(msg):
    print(f"{Fore.WHITE}[{datetime.now(ist).strftime('%H:%M:%S')}] {msg}", end="\r", flush=True)

def in_market_hours():
    now = datetime.now(ist)
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 29))

# =====================================================================
# CENTRAL WORKER DAEMON INTERFACE
# =====================================================================
def start_daemon():
    print(f"\n{Fore.GREEN}{Style.BRIGHT}📡 INIT: Master Automation Matrix Core Loop Launching Now...")
    print(f"Flat Trading Workspace Node: {HERE}")
    print(f"Mode: Simple Sequential Execution Loop | Global Cooldown Pause: {LOOP_INTERVAL}s")
    print("━" * 68)

    # =====================================================================
    # 📌 STAGE 1: MANDATORY INITIAL ONE-CYCLE RUN OF ALL WORKER SCRIPTS
    # =====================================================================
    print(f"{Fore.YELLOW}🔄 STAGE 1: Running compulsory initial sync cycle across all files...")
    run_script("_exit.py")
    run_script("_entry.py")
    print(f"{Fore.GREEN}✅ Initial synchronization run complete. Entering primary monitoring loops.")
    print("━" * 68)
    time.sleep(2)  # Brief display pause before engaging loop routines

    # =====================================================================
    # 🏁 STAGE 2: LOCKED CONTINUOUS DAEMON LOOP MONITOR
    # =====================================================================
    loop_counter = 1

    while True:
        if in_market_hours():
            for sub_itr in range(1, 31):
                if not in_market_hours():
                    break
                
                pos_summary = call_with_timeout(get_global_position_summary, 7, client)
                
                if pos_summary and isinstance(pos_summary, dict):
                    long_lots = pos_summary.get("long", 0)
                    short_lots = pos_summary.get("short", 0)
                else:
                    long_lots, short_lots = 0, 0

                live_status(f"📊 Loop#{loop_counter} Sub#{sub_itr} | Active CE Portfolio Ratios -> Long: {long_lots} L | Short: {short_lots} L")

                # -------- CORE EXECUTION DECISION GATES --------
                if SIMPLE_MODE:
                    run_script("_exit.py")
                    run_script("_entry.py")
                else:
                    if long_lots > 0 and long_lots == short_lots:
                        run_script("_exit.py")
                    elif long_lots == 0 and short_lots == 0:
                        run_script("_entry.py")
                    else:
                        run_script("_exit.py")
                        run_script("_entry.py")

                fancy_pause(LOOP_INTERVAL)
                loop_counter += 1
        else:
            clear_printed = False
            while not in_market_hours():
                if not clear_printed:
                    print(f"\n{Fore.BLUE}🌙 MARKET CLOSED: Master network core idling inside standby sleep state.")
                    clear_printed = True
                print(f"⏳ STANDBY: System paused. Waiting for market opening clock at 09:16 IST... ", end="\r", flush=True)
                time.sleep(10)
            print(f"\n{Fore.GREEN}📈 MARKET OPEN BOUNDARY DETECTED: Resuming live system loop arrays now.")

if __name__ == "__main__":
    try:
        start_daemon()
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}🛑 Core System terminated via user input command. Exiting cleanly.")
        sys.exit(0)
