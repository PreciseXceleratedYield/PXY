#!/usr/bin/env python3
import subprocess
import time
from datetime import datetime
from colorama import init, Fore, Style
import sys
from pathlib import Path

# ---------------- INIT ----------------
init(autoreset=True)

# ---------------- PATH SETUP ----------------
HERE = Path(__file__).resolve().parent
RUN_DIR = HERE / "run"
SYS_DIR = HERE.parent
for path in (RUN_DIR, HERE, SYS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from sysexepxy import send_telegram
from syshdaypxy import is_nse_fo_trading_day
from sysauditpxy import record as audit_record

# Component failures are reported periodically; they never stop the engine.
COMPONENT_FAILURES = {}
ENGINE_ITERATION = 0


def _record_component_failure(name, error=None):
    COMPONENT_FAILURES[name] = str(error or "execution failed")
    audit_record(name, "FAILED", error=COMPONENT_FAILURES[name])


def _record_component_recovery(name):
    COMPONENT_FAILURES.pop(name, None)
    audit_record(name, "OK")


def _notify_persistent_failures():
    if ENGINE_ITERATION % 5 != 0:
        return
    for name, error in list(COMPONENT_FAILURES.items()):
        send_telegram(
            f"⚠️ PXY component failure (iteration {ENGINE_ITERATION})\n"
            f"Component: {name}\nError: {error}\n"
            "Engine continues running; automatic retry remains in effect."
        )

from syscnfgpxy import (
    EXEPXYPXY_IDLE_PAUSE_SECONDS,
    EXEPXYPXY_IDLE_POLL_SECONDS,
    EXEPXYPXY_MARKET_CLOSE,
    EXEPXYPXY_MARKET_OPEN,
    EXEPXYPXY_PIPE_TIMEOUT_SECONDS,
    EXEPXYPXY_SUB_ITERATIONS,
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_TIMEZONE,
)

ist = SYSCNFGPXY_TIMEZONE

# ---------------- HELPER FUNCTIONS ----------------
def run_script(script_path, timeout=None):
    component = Path(script_path).name
    started = time.monotonic()
    audit_record(component, "START")
    if not Path(script_path).exists():
        error = f"script not found: {script_path}"
        _record_component_failure(component, error)
        print(f"⚠️ SKIP: {error}")
        print("━" * 42)
        return False
    try:
        subprocess.run([sys.executable, str(script_path)], check=True, timeout=timeout)
        audit_record(component, "COMPLETE", duration_seconds=round(time.monotonic() - started, 3))
        _record_component_recovery(component)
        print("━" * 42)
        return True
    except subprocess.TimeoutExpired:
        error = f"timed out after {timeout}s"
        print(f"⏱ TIMEOUT: {component} {error} ⚠️")
    except subprocess.CalledProcessError as exc:
        error = f"process exited with status {exc.returncode}"
        print(f"❌ RUN ERR: {component}: {error} ⚠️")
    except Exception as exc:
        error = str(exc)
        print(f"❌ RUN ERR: {component}: {error} ⚠️")
    audit_record(component, "COMPLETE", duration_seconds=round(time.monotonic() - started, 3), outcome="FAILED")
    _record_component_failure(component, error)
    print("━" * 42)
    return False

def safe_run(script_path, timeout=None):
    try:
        return run_script(script_path, timeout=timeout)
    except Exception as error:
        _record_component_failure(Path(script_path).name, error)
        print("⚠️ SAFE RUN: unexpected error occurred ⚠️")
        return False

def clear_screen():
    """Clear the terminal without invoking a shell command."""
    print("\033[2J\033[H", end="", flush=True)


def fancy_pause(seconds=EXEPXYPXY_IDLE_PAUSE_SECONDS):
    for i in range(seconds, 0, -1):
        print(f"⏳ Pause active... {Fore.YELLOW}{i}{Style.RESET_ALL}s", end="\r", flush=True)
        time.sleep(1)
    print("✅ Resume execution now ")

def live_status(msg):
    print(f"{datetime.now(ist).strftime('%H:%M:%S')} {msg}", end="\r", flush=True)

def _in_market_hours_production():
    now = datetime.now(ist)
    if not (0 <= now.weekday() <= 4 and EXEPXYPXY_MARKET_OPEN <= now.time() < EXEPXYPXY_MARKET_CLOSE):
        return False
    try:
        return is_nse_fo_trading_day(now.date())
    except Exception as error:
        print(f"⚠️ NSE trading calendar unavailable; execution cycle skipped: {error}")
        return False


def in_market_hours():
    return _in_market_hours_production()

def run_market_cycle():
    """Run one production iteration with maximum exit priority."""
    global ENGINE_ITERATION
    ENGINE_ITERATION += 1
    safe_run(RUN_DIR / "runnfutpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)
    safe_run(HERE / "exeexitpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)
    safe_run(HERE / "exeentrpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)
    safe_run(HERE / "exeexitpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)
    safe_run(HERE / "exeavgpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)
    safe_run(HERE / "exeexitpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)
    _notify_persistent_failures()
    fancy_pause(SYSCNFGPXY_ACTION_COOLDOWN_SECONDS)


def main():
    clear_screen()
    print("\n🚀 INIT: main market loop starting now [SIMPLE MODE ONLY] 📡")
    loop_counter = 1

    # Obtain one synchronous FUT quote before any startup signal/trading pass.
    # DTAF decides whether to use it or fall back to Yahoo OHLC.
    safe_run(RUN_DIR / "runnfutpxy.py", timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)

    parent_scripts = [
        HERE.parent / "sysdashpxy.py",
        HERE / "exeentrpxy.py",
        HERE / "exeexitpxy.py",
    ]
    for script in parent_scripts:
        safe_run(script, timeout=EXEPXYPXY_PIPE_TIMEOUT_SECONDS)

    while True:
        clear_screen()
        if in_market_hours():
            live_status("🚀 LOOP: waiting trigger 📊")
            for sub_itr in range(1, EXEPXYPXY_SUB_ITERATIONS + 1):
                clear_screen()
                print(
                    f"📊 Loop#{loop_counter} Sub#{sub_itr} | "
                    "Execution Stack Running..."
                )
                run_market_cycle()
            loop_counter += 1
        else:
            print("\n🌙 MKT CLOSED: running cleanup tasks now 💤")
            safe_run(HERE.parent / "sysslefpxy.py")
            fancy_pause(EXEPXYPXY_IDLE_PAUSE_SECONDS)

            while not in_market_hours():
                clear_screen()
                safe_run(HERE.parent / "syscprtpxy.py")
                print(
                    f" ⏳   WAIT : market opens at "
                    f"{EXEPXYPXY_MARKET_OPEN.strftime('%H:%M')} IST  📡",
                    end="\r",
                )
                time.sleep(EXEPXYPXY_IDLE_POLL_SECONDS)

            print("\n🚀 MKT OPEN: resuming main loop now 📈")


if __name__ == "__main__":
    raise SystemExit(main())
