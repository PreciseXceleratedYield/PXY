# execbuypxy.py
# COUNTER-BUY (CBUY) TRIGGER
#
# Called from exeexitpxy.py after the target exits. Receives the rows that are STILL held
# (rows just exited, or with an exit already in flight, are removed by the caller).
#
#   CE rows held + exit key BEAR + no PE row  -> run pxybuype  (buys the PE leg)
#   PE rows held + exit key BULL + no CE row  -> run pxybuyce  (buys the CE leg)
#
# pxybuype / pxybuyce are executable shell scripts (no extension); they are run directly,
# not through python3.
#
# Anything else (including an exit key that is not BULL/BEAR) -> no action.
import os
import shutil
import json
import time
import pytz
import subprocess
import pandas as pd
from datetime import datetime, time as dt_time
from colorama import Fore, Style

# ==================== CONFIG (this file's settings) ====================
CBUY_ACTION = "YES"            # "YES" = run the counter-buy script; "NO" = passive, only prints what it would do
CBUY_LOCK_SECS = 30            # do not re-fire the same counter-buy script within this many seconds (0 = off).
                               # The script is fire-and-forget (login + order takes time), so keep this >= 30.
CBUY_CUTOFF = dt_time(15, 10)  # no counter-buy from 15:10, before square-off starts
EXIT_KEY_COLUMN = "exit"       # market column holding the BULL / BEAR exit key (keep same as in exetgtpxy.py)
CBUY_SCRIPTS = {               # held side -> executable that buys the opposite (protective) leg
    "CE": "pxybuype",
    "PE": "pxybuyce",
}
CBUY_LOCK_FILE_NAME = ".cbuy_lock.json"
CBUY_MAX_PER_DAY = 6           # hard cap on counter-buy launches per IST day (0 = off). A buy that keeps failing cannot loop forever.
CBUY_COUNT_FILE_NAME = ".cbuy_count.json"
CBUY_LOCK_KEEP_SECS = 600      # lock entries older than max(this, 2 * CBUY_LOCK_SECS) are pruned
DEBUG_MODE = True              # verbose counter-buy decisions (turn off after Monday)
# =======================================================================

_LOCK_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), CBUY_LOCK_FILE_NAME)
_COUNT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), CBUY_COUNT_FILE_NAME)
_IST = pytz.timezone("Asia/Kolkata")
_cap_warned = False


def debug_log(msg, color=Fore.BLUE):
    if DEBUG_MODE:
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}")


# ---------------- small helpers ----------------
def _load_locks():
    """Reads the lock file; returns {} if missing/unreadable. Never raises."""
    try:
        if os.path.exists(_LOCK_FILE):
            with open(_LOCK_FILE, "r") as fh:
                return json.load(fh)
    except Exception:
        pass
    return {}


def _recent(data, key, secs):
    """True if `key` was recorded within `secs` seconds. Never raises."""
    if secs <= 0:
        return False
    try:
        return (time.time() - float(data.get(key, 0))) < secs
    except Exception:
        return False


def _mark_lock(key):
    """Records `key` with the current time; prunes stale entries. Never raises."""
    try:
        data = _load_locks()
        now = time.time()
        keep_secs = max(CBUY_LOCK_KEEP_SECS, CBUY_LOCK_SECS * 2)
        data = {k: v for k, v in data.items() if now - float(v) < keep_secs}
        data[key] = now
        tmp = _LOCK_FILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(data, fh)
        os.replace(tmp, _LOCK_FILE)
    except Exception:
        pass


def _find_script(name):
    """Looks for the executable next to this file, then one folder up, then on PATH.
    Returns a path or None."""
    here = os.path.dirname(os.path.abspath(__file__))
    for folder in (here, os.path.dirname(here)):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return shutil.which(name)


def _is_executable(path):
    return os.access(path, os.X_OK)


def _today():
    return datetime.now(_IST).strftime("%Y-%m-%d")


def _fires_today():
    """Counter-buy launches already made today (IST). Never raises."""
    try:
        if os.path.exists(_COUNT_FILE):
            with open(_COUNT_FILE, "r") as fh:
                d = json.load(fh)
            if isinstance(d, dict) and d.get("date") == _today():
                return int(d.get("count", 0))
    except Exception:
        pass
    return 0


def _count_fire():
    """Adds one launch to today's count. Never raises."""
    try:
        tmp = _COUNT_FILE + ".tmp"
        with open(tmp, "w") as fh:
            json.dump({"date": _today(), "count": _fires_today() + 1}, fh)
        os.replace(tmp, _COUNT_FILE)
    except Exception:
        pass


# ---------------- main entry ----------------
def check_counter_leg(remaining_df):
    """remaining_df: rows still held after this cycle's target exits.
    Returns the name of the script fired (or None). Never raises."""
    try:
        if remaining_df is None or remaining_df.empty:
            debug_log("Counter check: no rows remaining after exits.")
            return None

        state = str(remaining_df.iloc[0].get(EXIT_KEY_COLUMN, "NONE")).upper().strip()
        if state not in ("BULL", "BEAR"):
            debug_log(f"Counter check: exit key '{state}' is not BULL/BEAR; skipping.")
            return None

        symbols = remaining_df["symbol"].astype(str).str.upper().str.strip()
        qty = pd.to_numeric(remaining_df["qty"], errors="coerce").fillna(0)
        has_ce = bool((symbols.str.endswith("CE") & (qty > 0)).any())
        has_pe = bool((symbols.str.endswith("PE") & (qty > 0)).any())

        if state == "BEAR" and has_ce and not has_pe:
            held, counter = "CE", "PE"
        elif state == "BULL" and has_pe and not has_ce:
            held, counter = "PE", "CE"
        else:
            debug_log(f"Counter check: state {state} | CE rows: {has_ce} | PE rows: {has_pe} -> no action.")
            return None

        script_name = CBUY_SCRIPTS[held]

        IST = pytz.timezone("Asia/Kolkata")
        if datetime.now(IST).time() >= CBUY_CUTOFF:
            debug_log(f"Counter check: past {CBUY_CUTOFF}; not firing {script_name}.")
            return None

        lock_key = f"CBUY|{script_name}"
        if _recent(_load_locks(), lock_key, CBUY_LOCK_SECS):
            debug_log(f"Counter check: {script_name} already fired within {CBUY_LOCK_SECS}s.")
            return None

        global _cap_warned
        if CBUY_MAX_PER_DAY > 0 and _fires_today() >= CBUY_MAX_PER_DAY:
            if not _cap_warned:
                _cap_warned = True
                print(f"{Fore.RED}🛑 Counter-buy daily cap reached ({CBUY_MAX_PER_DAY} launches); not firing {script_name}.")
            return None

        print(f"{Fore.YELLOW}⚠️ Hostile state ({state}): remaining {held} rows with NO {counter} leg.")
        if str(CBUY_ACTION).upper().strip() != "YES":
            print(f"{Fore.BLUE}{Style.BRIGHT}ℹ️ [PASSIVE ALERT] CBUY_ACTION=NO. Would fire {script_name}.")
            return None

        path = _find_script(script_name)
        if not path:
            print(f"{Fore.RED}❌ Counter script {script_name} not found (looked next to execbuypxy.py, one folder up, and on PATH).")
            return None
        if not _is_executable(path):
            print(f"{Fore.RED}❌ {path} is not executable (run: chmod +x {path}).")
            return None

        # shell script: run it directly, not through python3
        # lock + count BEFORE the launch: a duplicate buy is worse than a short wait
        _mark_lock(lock_key)
        _count_fire()
        subprocess.Popen([path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ FIRED COUNTER-BUY: {script_name}")
        return script_name
    except Exception as e:
        print(f"{Fore.RED}❌ Counter-check error: {e}")
        return None
