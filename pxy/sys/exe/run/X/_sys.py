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
from _sgnl import _pad_line_to_42  # Shared 42-character width constraint engine
from sysmodepxy import dispatch_mode

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
from _entr import get_global_position_summary

# --- INITIALIZE SHARED BROKER CLIENT ONCE AT BOOT ---
try:
    from _clnt import get_session
    client = get_session()
    if not client:
        err_msg = "❌ FATAL: Broker session instantiation failed"
        print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))
        sys.exit(1)
    ok_msg = "✅ SESSION LIVE: Client channel online"
    print(_pad_line_to_42(ok_msg, Fore.GREEN, Style.RESET_ALL))
except Exception as e:
    err_msg = f"❌ Client Init Failed: {str(e)[:20]}"
    print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))
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
            err_msg = "⏱ API TIMEOUT: Req exceeded 7s limit ⚠️"
            print(f"\n{_pad_line_to_42(err_msg, Fore.YELLOW, Style.RESET_ALL)}")
            return None
        except Exception as e:
            err_msg = f"❌ API ERROR: Position call failure ⚠️"
            print(f"\n{_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL)}")
            return None

# =====================================================================
# CONTROLLED SUBPROCESS SCRIPT EXECUTION ENGINE (FLAT PATH)
# =====================================================================
def run_script(script_name):
    """Executes target script residing flatly in the same directory."""
    script_path = HERE / script_name
    if not script_path.exists():
        if DEBUG_MODE: 
            err_msg = f"⚠️ SKIP: Asset not found -> {script_name[:15]}"
            print(_pad_line_to_42(err_msg, Fore.YELLOW, Style.RESET_ALL))
        return
    try:
        subprocess.run(['python3', str(script_path)], check=True, timeout=20)
    except subprocess.TimeoutExpired:
        err_msg = f"⏱ TIMEOUT: Subprocess frozen -> {script_name[:12]} ⚠️"
        print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))
    except subprocess.CalledProcessError:
        err_msg = f"❌ RUN ERR: Bad exit code -> {script_name[:15]} ⚠️"
        print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))
    except Exception as e:
        err_msg = f"❌ RUN ERR: Subprocess fail -> {script_name[:14]} ⚠️"
        print(_pad_line_to_42(err_msg, Fore.RED, Style.RESET_ALL))

def fancy_pause(seconds=7):
    """Enforces clean countdown timer inside terminal line buffer."""
    for i in range(seconds, 0, -1):
        pause_str = f"⏳ Cooldown active... {i}s"
        print(_pad_line_to_42(pause_str, Fore.YELLOW, Style.RESET_ALL), end="\r", flush=True)
        time.sleep(1)
    ok_msg = "✅ System ready for next iteration"
    print(_pad_line_to_42(ok_msg, Fore.GREEN, Style.RESET_ALL))

# =====================================================================
# FIXED SYNTAX BUG LINE: Cleaned the string format syntax token safely
# =====================================================================
def live_status(msg):
    t_stamp = datetime.now(ist).strftime('%H%M%S')
    combined = f"📡 {t_stamp} | {msg}"
    print(_pad_line_to_42(combined, Fore.WHITE, Style.RESET_ALL), end="\r", flush=True)

def _in_market_hours_production():
    now = datetime.now(ist)
    return (0 <= now.weekday() <= 4 and dt_time(9, 16) <= now.time() <= dt_time(15, 29))


def in_market_hours():
    return dispatch_mode("engine_window_open", _in_market_hours_production)

# =====================================================================
# CENTRAL WORKER DAEMON INTERFACE
# =====================================================================
def start_daemon():
    if not dispatch_mode("legacy_engine_enabled", lambda: True):
        print("TST MODE: legacy engine disabled; use the active test-mode engine.")
        return

    border = "==========================================" # 42 chars
    print(f"\n{_pad_line_to_42('📡 INIT: Master Core Automation Loop', Fore.GREEN + Style.BRIGHT, Style.RESET_ALL)}")
    print(_pad_line_to_42(border, Fore.GREEN, Style.RESET_ALL))

    # =====================================================================
    # 📌 STAGE 1: MANDATORY INITIAL ONE-CYCLE RUN OF ALL WORKER SCRIPTS
    # =====================================================================
    print(_pad_line_to_42("🔄 STAGE 1: Compulsory Sync Run...", Fore.YELLOW, Style.RESET_ALL))
    run_script("_exit.py")
    run_script("_entr.py")
    print(_pad_line_to_42("✅ Initial synchronization complete", Fore.GREEN, Style.RESET_ALL))
    print(_pad_line_to_42(border, Fore.GREEN, Style.RESET_ALL))
    time.sleep(2)

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

                # Fits beautifully inside 42 width boundary layout constraints
                live_status(f"L#{loop_counter} S#{sub_itr} | L:{long_lots} | S:{short_lots}")

                # -------- CORE EXECUTION DECISION GATES --------
                if SIMPLE_MODE:
                    run_script("_exit.py")
                    run_script("_entr.py")
                else:
                    if long_lots > 0 and long_lots == short_lots:
                        run_script("_exit.py")
                    elif long_lots == 0 and short_lots == 0:
                        run_script("_entr.py")
                    else:
                        run_script("_exit.py")
                        run_script("_entr.py")

                fancy_pause(LOOP_INTERVAL)
                loop_counter += 1
        elif dispatch_mode("run_closed_market_tasks", lambda: True):
            clear_printed = False
            while not in_market_hours():
                if not clear_printed:
                    print(f"\n{_pad_line_to_42('🌙 MARKET CLOSED: Master node idling', Fore.BLUE, Style.RESET_ALL)}")
                    clear_printed = True
                print(_pad_line_to_42("⏳ STANDBY: Awaiting 09:16 Market Clock", Fore.BLUE, Style.RESET_ALL), end="\r", flush=True)
                time.sleep(10)
            print(f"\n{_pad_line_to_42('📈 MARKET OPEN: Resuming loop arrays', Fore.GREEN, Style.RESET_ALL)}")
        else:
            print("TST MODE: legacy engine paused during market hours.")
            time.sleep(10)

if __name__ == "__main__":
    try:
        start_daemon()
    except KeyboardInterrupt:
        print(f"\n{_pad_line_to_42('🛑 System terminated by user command', Fore.YELLOW, Style.RESET_ALL)}")
        sys.exit(0)
