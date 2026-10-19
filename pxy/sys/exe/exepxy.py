#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime
from colorama import init, Fore, Style
import sys
from pathlib import Path
import os  # ✅ Kept for screen clearing

# ---------------- INIT ----------------
init(autoreset=True)

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
SYS_DIR = HERE.parent
for path in (RUN_DIR, HERE, SYS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from syscnfgpxy import (
    EXEPXYPXY_IDLE_PAUSE_SECONDS,
    EXEPXYPXY_IDLE_POLL_SECONDS,
    EXEPXYPXY_MARKET_CLOSE,
    EXEPXYPXY_MARKET_OPEN,
    EXEPXYPXY_PIPE_TIMEOUT_SECONDS,
    EXEPXYPXY_SUB_ITERATIONS,
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_TIMEZONE,
    SYSMODEPXY_RUN_MODE as RUNMODE,
)
from sysmodepxy import normal_start_message

ist = SYSCNFGPXY_TIMEZONE

if RUNMODE != "PRD":
    _normal_start_error = normal_start_message(RUNMODE)
else:
    _normal_start_error = None

from sysmodepxy import dispatch_mode

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_path, timeout=None):
    if not Path(script_path).exists():
        print(f"⚠️ SKIP: script not found -> {script_path}")
        print("━" * 42)
        return
    try:
        # ✅ Dynamic timeout value is passed here (None means run forever)
        subprocess.run([sys.executable, str(script_path)], check=True, timeout=timeout)
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

def fancy_pause(seconds=EXEPXYPXY_IDLE_PAUSE_SECONDS):
    for i in range(seconds, 0, -1):
        print(f"⏳ Pause active... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
        time.sleep(1)
    print("✅ Resume execution now ")

def live_status(msg):
    print(f"{datetime.now(ist).strftime('%H:%M:%S')} {msg}", end="\r", flush=True)

def _in_market_hours_production():
    now = datetime.now(ist)
    return (
        0 <= now.weekday() <= 4
        and EXEPXYPXY_MARKET_OPEN <= now.time() <= EXEPXYPXY_MARKET_CLOSE
    )

def in_market_hours():
    return dispatch_mode("engine_window_open", _in_market_hours_production)

def is_exit_window():
    """Verify if the active engine time falls inside the strict 09:15 to 10:15 window."""
    now = datetime.now(ist).time()
    start_window = datetime.strptime("09:15", "%H:%M").time()
    end_window = datetime.strptime("10:15", "%H:%M").time()
    return start_window <= now <= end_window

def run_market_cycle():
    """Run one production iteration with conditional exit windows and maximum priority."""
    
    # --- PASS 1: Early Exit Evaluation (Conditional) ---
    if is_exit_window():
        safe_run(HERE / "exeexitpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)
    else:
        print(f"⏳ {datetime.now(ist).strftime('%H:%M:%S')} | SKIP: exeexitpxy.py (Outside 09:15-10:15 window)")
        print("━" * 42)

    # --- PASS 2: Primary Strategy Core Entry ---
    safe_run(HERE / "exeentrpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)

    # --- PASS 3: Intermediate Exit Evaluation (Conditional) ---
    if is_exit_window():
        safe_run(HERE / "exeexitpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)

    # --- PASS 4: Average Accumulation Phase ---
    safe_run(HERE / "exeavgpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)

    # --- PASS 5: Late Cycle Exit Evaluation (Conditional) ---
    if is_exit_window():
        safe_run(HERE / "exeexitpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)

    fancy_pause(SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)


def main():
    if _normal_start_error is not None:
        print(_normal_start_error, file=sys.stderr)
        return 2

    os.system("clear")
    print("\n🚀 INIT: main market loop starting now [SIMPLE MODE ONLY] 📡")
    loop_counter = 1

    parent_scripts = [
        HERE.parent / "sysdashpxy.py",
        HERE / "exeentrpxy.py",
        HERE / "exeexitpxy.py",
    ]
    
    # --- STARTUP CHECKS ---
    if dispatch_mode("run_startup_checks", lambda: True):
        for script in parent_scripts:
            # Conditional time window filter specifically tracking the startup pass for exeexitpxy
            if script.name == "exeexitpxy.py" and not is_exit_window():
                print(f"⏳ Startup | SKIP: exeexitpxy.py (Outside 09:15-10:15 window)")
                print("━" * 42)
                continue
            safe_run(script)
    else:
        print("CHK MODE: engine startup checks paused during market hours.")

    while True:
        if in_market_hours():
            live_status("🚀 LOOP: waiting trigger 📊")
            for sub_itr in range(1, EXEPXYPXY_SUB_ITERATIONS + 1):
                os.system("clear")
                print(
                    f"📊 Loop#{loop_counter} Sub#{sub_itr} | "
                    "Execution Stack Running..."
                )
                run_market_cycle()
            loop_counter += 1
        else:
            os.system("clear")
            if dispatch_mode("run_closed_market_tasks", lambda: True):
                print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
                safe_run(HERE.parent / "sysslefpxy.py")
            else:
                print("\nCHK MODE: engine paused during market hours.")
            fancy_pause(EXEPXYPXY_IDLE_PAUSE_SECONDS)

            while not in_market_hours():
                os.system("clear")
                if dispatch_mode("run_closed_market_tasks", lambda: True):
                    print(f" ⏳   WAIT : market opens at 09:16 IST  📡 (Checked at {datetime.now(ist).strftime('%H:%M:%S')})", end="\r")
                    safe_run(HERE.parent / "syscprtpxy.py")
                else:
                    print(" ⏳   CHK waits until market close  📡", end="\r")
                time.sleep(EXEPXYPXY_IDLE_POLL_SECONDS)

            print("\n🚀 MKT OPEN: resuming main loop now 📈")


if __name__ == "__main__":
    raise SystemExit(main())

