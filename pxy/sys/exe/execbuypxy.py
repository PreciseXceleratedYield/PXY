# execbuypxy.py
# COUNTER-BUY (CBUY) TRIGGER
#
# Called from exeexitpxy.py after the target exits. Receives rows still held.
#   CE rows held + no PE row -> run pxybuype
#   PE rows held + no CE row -> run pxybuyce
#
# Duplicate prevention is serialized across processes with flock. If the cooldown
# lock cannot be read or persisted, this module fails closed and does not launch
# a counter-buy wrapper.

import os
import shutil
import json
import time
import subprocess
import fcntl
from datetime import datetime
from colorama import Fore, Style
from syscnfgpxy import (
    EXECBUYPXY_ACTION,
    EXECBUYPXY_CUTOFF,
    EXECBUYPXY_DEBUG_ENABLED,
    EXECBUYPXY_LOCK_KEEP_SECS,
    EXECBUYPXY_MAX_PER_DAY,
    EXECBUYPXY_SCRIPTS,
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_TIMEZONE,
)
from sysdecisionpxy import counter_leg_permission_status, counter_leg_script

CBUY_ACTION = EXECBUYPXY_ACTION
CBUY_LOCK_SECS = SYSCNFGPXY_ACTION_COOLDOWN_SECONDS
CBUY_CUTOFF = EXECBUYPXY_CUTOFF
CBUY_SCRIPTS = EXECBUYPXY_SCRIPTS
CBUY_LOCK_FILE_NAME = ".cbuy_lock.json"
CBUY_COUNT_FILE_NAME = ".cbuy_count.json"
CBUY_GUARD_FILE_NAME = ".cbuy_guard.lock"
CBUY_MAX_PER_DAY = EXECBUYPXY_MAX_PER_DAY
CBUY_LOCK_KEEP_SECS = EXECBUYPXY_LOCK_KEEP_SECS
EXIT_KEY_COLUMN = "exit"

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCK_FILE = os.path.join(_BASE_DIR, CBUY_LOCK_FILE_NAME)
_COUNT_FILE = os.path.join(_BASE_DIR, CBUY_COUNT_FILE_NAME)
_GUARD_FILE = os.path.join(_BASE_DIR, CBUY_GUARD_FILE_NAME)
_IST = SYSCNFGPXY_TIMEZONE
_cap_warned = False


def debug_log(msg, color=Fore.BLUE):
    if EXECBUYPXY_DEBUG_ENABLED:
        print(f"{color}[DEBUG] {msg}{Style.RESET_ALL}")


def _load_locks():
    """Load cooldown data; a missing file means no previous cooldowns."""
    if not os.path.exists(_LOCK_FILE):
        return {}
    with open(_LOCK_FILE, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid counter-buy lock data in {_LOCK_FILE}")
    return data


def _recent(data, key, secs):
    """Return whether key was recorded within secs seconds."""
    if secs <= 0:
        return False
    try:
        return (time.time() - float(data.get(key, 0))) < secs
    except (TypeError, ValueError, OverflowError):
        return False


def _atomic_json_write(path, data):
    """Write JSON through a unique temporary file and atomically replace path."""
    tmp = f"{path}.{os.getpid()}.{time.time_ns()}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass


def _mark_lock(key):
    """Persist cooldown; errors propagate so a buy is not launched without a lock."""
    data = _load_locks()
    now = time.time()
    keep_secs = max(CBUY_LOCK_KEEP_SECS, CBUY_LOCK_SECS * 2)
    cleaned = {}
    for old_key, value in data.items():
        try:
            if now - float(value) < keep_secs:
                cleaned[old_key] = value
        except (TypeError, ValueError, OverflowError):
            continue
    cleaned[key] = now
    _atomic_json_write(_LOCK_FILE, cleaned)


def _find_script(name):
    """Search the engine, system, and PXY directories, then PATH."""
    here = _BASE_DIR
    for folder in (here, os.path.dirname(here), os.path.dirname(os.path.dirname(here))):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return shutil.which(name)


def _today():
    return datetime.now(_IST).strftime("%Y-%m-%d")


def _fires_today():
    """Read the daily counter; used only for bookkeeping, as in existing behavior."""
    try:
        if os.path.exists(_COUNT_FILE):
            with open(_COUNT_FILE, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and data.get("date") == _today():
                return int(data.get("count", 0))
    except Exception:
        pass
    return 0


def _count_fire():
    """Best-effort daily launch counter; cooldown lock is the safety control."""
    try:
        _atomic_json_write(
            _COUNT_FILE,
            {"date": _today(), "count": _fires_today() + 1},
        )
    except Exception:
        pass


def _check_counter_leg_locked(remaining_df):
    """Check and, if allowed, launch a counter-buy while guard lock is held."""
    try:
        if remaining_df is None or remaining_df.empty:
            debug_log("Counter check: no rows remaining after exits.")
            return None

        signal = str(remaining_df.iloc[0].get(EXIT_KEY_COLUMN, "NONE")).upper().strip()
        records = remaining_df[["symbol", "qty"]].to_dict("records")
        script_name = counter_leg_script(signal, records, CBUY_SCRIPTS)
        if script_name is None:
            debug_log(
                f"Counter check: exit signal {signal} does not oppose exactly "
                "one held option side."
            )
            return None

        held = "PE" if signal == "BULL" else "CE"
        counter = "PE" if held == "CE" else "CE"
        now = datetime.now(_IST).time()
        lock_key = f"CBUY|{script_name}"

        # Fail closed on lock-file read/parse errors. Do not assume unlocked.
        locked = _recent(_load_locks(), lock_key, CBUY_LOCK_SECS)
        launches_today = 0  # Preserve existing behavior: daily cap is not enforced here.
        permission = counter_leg_permission_status(
            now,
            CBUY_CUTOFF,
            locked,
            launches_today,
            CBUY_MAX_PER_DAY,
            str(CBUY_ACTION).upper().strip() == "YES",
        )

        if permission == "cutoff":
            debug_log(f"Counter check: past {CBUY_CUTOFF}; not firing {script_name}.")
            return None
        if permission == "locked":
            debug_log(f"Counter check: {script_name} already fired within {CBUY_LOCK_SECS}s.")
            return None

        global _cap_warned
        if permission == "daily_limit":
            if not _cap_warned:
                _cap_warned = True
                print(
                    f"{Fore.RED}🛑 Counter-buy daily cap reached "
                    f"({CBUY_MAX_PER_DAY} launches); not firing {script_name}."
                )
            return None

        print(f"{Fore.YELLOW}⚠️ Exit signal ({signal}): remaining {held} rows with NO {counter} leg.")
        if permission == "passive":
            print(f"{Fore.BLUE}{Style.BRIGHT}ℹ️ [PASSIVE ALERT] CBUY_ACTION=NO. Would fire {script_name}.")
            return None

        path = _find_script(script_name)
        if not path:
            print(
                f"{Fore.RED}❌ Counter script {script_name} not found "
                "(searched the engine, system, PXY, and PATH locations)."
            )
            return None

        # Save cooldown before launch. If this fails, the exception path prevents launch.
        _mark_lock(lock_key)
        _count_fire()
        subprocess.Popen(["bash", path])
        print(f"{Fore.MAGENTA}{Style.BRIGHT}⚡ FIRED COUNTER-BUY: {script_name}")
        return script_name

    except Exception as e:
        print(f"{Fore.RED}❌ Counter-check error; counter-buy NOT launched: {e}")
        return None


def check_counter_leg(remaining_df):
    """Serialize check, cooldown update, and launch across concurrent processes."""
    try:
        # Linux/POSIX flock releases automatically when the file closes.
        with open(_GUARD_FILE, "a", encoding="utf-8") as guard:
            fcntl.flock(guard.fileno(), fcntl.LOCK_EX)
            return _check_counter_leg_locked(remaining_df)
    except Exception as e:
        print(f"{Fore.RED}❌ Counter-buy guard unavailable; counter-buy NOT launched: {e}")
        return None
