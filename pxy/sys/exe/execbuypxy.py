# execbuypxy.py
# COUNTER-BUY (CBUY) TRIGGER
#
# Called from exeexitpxy.py after the target exits. Receives the rows that are STILL held
# (rows just exited, or with an exit already in flight, are removed by the caller).
#
#   CE rows held + no PE row -> run pxybuype <offset>  (buys the PE leg)
#   PE rows held + no CE row -> run pxybuyce <offset>  (buys the CE leg)
#
# Offset logic:
#   ITM CE (strike < underlying price) -> offset 0
#   ITM PE (strike > underlying price) -> offset 0
#   ATM -> offset 0
#   Otherwise -> absolute difference rounded to nearest strike step
#
# Exactly one held side and an opposing exit signal are required.

import os
import shutil
import json
import time
import subprocess
import pandas as pd
from datetime import datetime
from colorama import Fore, Style

from syscnfgpxy import (
    EXECBUYPXY_ACTION,
    EXECBUYPXY_CUTOFF,
    EXECBUYPXY_DEBUG_ENABLED,
    EXECBUYPXY_LOCK_KEEP_SECS,
    EXECBUYPXY_MAX_PER_DAY,
    EXECBUYPXY_SCRIPTS,
    RUNNIFTYPXY_STRIKE_STEP,
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_TIMEZONE,
)

from sysdecisionpxy import counter_leg_permission_status, counter_leg_script


# ==================== CONFIG (this file's settings) ====================
CBUY_ACTION = EXECBUYPXY_ACTION
CBUY_LOCK_SECS = SYSCNFGPXY_ACTION_COOLDOWN_SECONDS
CBUY_CUTOFF = EXECBUYPXY_CUTOFF
CBUY_SCRIPTS = EXECBUYPXY_SCRIPTS
CBUY_LOCK_FILE_NAME = ".cbuy_lock.json"
CBUY_MAX_PER_DAY = EXECBUYPXY_MAX_PER_DAY
CBUY_COUNT_FILE_NAME = ".cbuy_count.json"
CBUY_LOCK_KEEP_SECS = EXECBUYPXY_LOCK_KEEP_SECS
EXIT_KEY_COLUMN = "exit"
# =======================================================================

_LOCK_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    CBUY_LOCK_FILE_NAME,
)
_COUNT_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    CBUY_COUNT_FILE_NAME,
)
_IST = SYSCNFGPXY_TIMEZONE
_cap_warned = False


def debug_log(msg, color=Fore.BLUE):
    if EXECBUYPXY_DEBUG_ENABLED:
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
    """Search the engine, system, and PXY directories, then PATH."""
    here = os.path.dirname(os.path.abspath(__file__))
    for folder in (
        here,
        os.path.dirname(here),
        os.path.dirname(os.path.dirname(here)),
    ):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            return path
    return shutil.which(name)


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


def _counter_buy_offset(remaining_df):
    """Return zero for an ITM/ATM held option; otherwise rounded offset.

    CE is ITM when strike < underlying price.
    PE is ITM when strike > underlying price.

    Returns None if the strike or underlying price cannot be determined safely.
    """
    if remaining_df is None or remaining_df.empty:
        return None

    if not {"symbol", "price"}.issubset(remaining_df.columns):
        return None

    symbols = remaining_df["symbol"].astype(str).str.upper()
    parsed = symbols.str.extract(r"(\d+)(CE|PE)$")

    if parsed.isna().any().any():
        return None

    strikes = parsed[0].astype(int).unique()
    option_types = parsed[1].unique()

    # Do not guess if multiple strikes or option types are present.
    if len(strikes) != 1 or len(option_types) != 1:
        return None

    strike = strikes[0]
    option_type = option_types[0]

    prices = pd.to_numeric(
        remaining_df["price"],
        errors="coerce",
    ).dropna()

    if prices.empty:
        return None

    price = float(prices.iloc[0])
    step = RUNNIFTYPXY_STRIKE_STEP

    if not pd.notna(price) or price <= 0 or step <= 0:
        return None

    # ITM CE: strike below underlying price.
    if option_type == "CE" and strike < price:
        return 0

    # ITM PE: strike above underlying price.
    if option_type == "PE" and strike > price:
        return 0

    # Exact ATM.
    if strike == price:
        return 0

    # Otherwise, round the absolute difference to the nearest strike step.
    difference = abs(strike - price)
    return int((difference + step / 2) // step * step)


# ---------------- main entry ----------------
def check_counter_leg(remaining_df):
    """remaining_df: rows still held after this cycle's target exits.

    Returns the name of the script fired (or None). Never raises.
    """
    try:
        if remaining_df is None or remaining_df.empty:
            debug_log("Counter check: no rows remaining after exits.")
            return None

        signal = str(
            remaining_df.iloc[0].get(EXIT_KEY_COLUMN, "NONE")
        ).upper().strip()

        records = remaining_df[["symbol", "qty"]].to_dict("records")

        script_name = counter_leg_script(
            signal,
            records,
            CBUY_SCRIPTS,
        )

        if script_name is None:
            debug_log(
                f"Counter check: exit signal {signal} does not oppose exactly "
                "one held option side."
            )
            return None

        # Calculate offset from the held option strike and underlying price.
        offset = _counter_buy_offset(remaining_df)

        if offset is None:
            print(
                f"{Fore.YELLOW}⚠️ Counter-buy skipped: "
                "could not safely calculate strike offset."
            )
            return None

        held = "PE" if signal == "BULL" else "CE"
        counter = "PE" if held == "CE" else "CE"

        now = datetime.now(_IST).time()
        lock_key = f"CBUY|{script_name}"
        locked = _recent(_load_locks(), lock_key, CBUY_LOCK_SECS)

        # Preserve the existing counter-buy permission behaviour.
        launches_today = 0

        permission = counter_leg_permission_status(
            now,
            CBUY_CUTOFF,
            locked,
            launches_today,
            CBUY_MAX_PER_DAY,
            str(CBUY_ACTION).upper().strip() == "YES",
        )

        if permission == "cutoff":
            debug_log(
                f"Counter check: past {CBUY_CUTOFF}; not firing {script_name}."
            )
            return None

        if permission == "locked":
            debug_log(
                f"Counter check: {script_name} already fired "
                f"within {CBUY_LOCK_SECS}s."
            )
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

        print(
            f"{Fore.YELLOW}⚠️ Exit signal ({signal}): "
            f"remaining {held} rows with NO {counter} leg."
        )

        if permission == "passive":
            print(
                f"{Fore.BLUE}{Style.BRIGHT}ℹ️ [PASSIVE ALERT] "
                f"CBUY_ACTION=NO. Would fire {script_name} with offset {offset}."
            )
            return None

        path = _find_script(script_name)

        if not path:
            print(
                f"{Fore.RED}❌ Counter script {script_name} not found "
                "(searched the engine, system, PXY, and PATH locations)."
            )
            return None

        # Lock and count before launch to reduce duplicate counter-buy orders.
        # Lock and count before launch to reduce duplicate counter-buy orders.
        _mark_lock(lock_key)
        _count_fire()

        # FIX: Added DEVNULL routing and start_new_session to prevent parent engine crashes
        subprocess.Popen(
            ["bash", path, str(offset)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        print(
            f"{ Fore. MAGENTA}{ Style. BRIGHT} ⚡ FIRED COUNTER-BUY: "
            f"{ script_name} { offset}"
        )


        print(
            f"{Fore.MAGENTA}{Style.BRIGHT}⚡ FIRED COUNTER-BUY: "
            f"{script_name} {offset}"
        )

        return script_name

    except Exception as e:
        print(f"{Fore.RED}❌ Counter-check error: {e}")
        return None
