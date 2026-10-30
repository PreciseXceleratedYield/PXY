
# execbuypxy.py
# COUNTER-BUY (CBUY) TRIGGER
#
# CE rows held + no PE row -> run pxybuype <offset>
# PE rows held + no CE row -> run pxybuyce <offset>
#
# Offset logic:
#   ATM / ITM -> 0
#   OTM       -> difference rounded to nearest 50
#
# The calculated offset is passed directly to the shell script.
# No weekday adjustment or additional offset is applied.

EXECBUYPXY_USE_DYNAMIC_STRIKE = True
STRIKE_STEP = 50

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
    SYSCNFGPXY_ACTION_COOLDOWN_SECONDS,
    SYSCNFGPXY_TIMEZONE,
)

from sysdecisionpxy import (
    counter_leg_permission_status,
    counter_leg_script,
)


# ==================== CONFIG ====================

CBUY_ACTION = EXECBUYPXY_ACTION
CBUY_LOCK_SECS = SYSCNFGPXY_ACTION_COOLDOWN_SECONDS
CBUY_CUTOFF = EXECBUYPXY_CUTOFF
CBUY_SCRIPTS = EXECBUYPXY_SCRIPTS

CBUY_LOCK_FILE_NAME = ".cbuy_lock.json"
CBUY_MAX_PER_DAY = EXECBUYPXY_MAX_PER_DAY
CBUY_COUNT_FILE_NAME = ".cbuy_count.json"
CBUY_LOCK_KEEP_SECS = EXECBUYPXY_LOCK_KEEP_SECS

EXIT_KEY_COLUMN = "exit"

# ================================================


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
    """Reads the lock file; returns {} if missing/unreadable."""
    try:
        if os.path.exists(_LOCK_FILE):
            with open(_LOCK_FILE, "r") as fh:
                return json.load(fh)
    except Exception:
        pass

    return {}


def _recent(data, key, secs):
    """True if key was recorded within secs seconds."""
    if secs <= 0:
        return False

    try:
        return (time.time() - float(data.get(key, 0))) < secs
    except Exception:
        return False


def _mark_lock(key):
    """Records the current time and prunes stale entries."""
    try:
        data = _load_locks()
        now = time.time()

        keep_secs = max(
            CBUY_LOCK_KEEP_SECS,
            CBUY_LOCK_SECS * 2,
        )

        data = {
            k: v
            for k, v in data.items()
            if now - float(v) < keep_secs
        }

        data[key] = now

        tmp = _LOCK_FILE + ".tmp"

        with open(tmp, "w") as fh:
            json.dump(data, fh)

        os.replace(tmp, _LOCK_FILE)

    except Exception:
        pass


def _find_script(name):
    """Search engine, system, and PXY directories, then PATH."""

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
    """Counter-buy launches already made today."""

    try:
        if os.path.exists(_COUNT_FILE):
            with open(_COUNT_FILE, "r") as fh:
                data = json.load(fh)

            if (
                isinstance(data, dict)
                and data.get("date") == _today()
            ):
                return int(data.get("count", 0))

    except Exception:
        pass

    return 0


def _count_fire():
    """Adds one launch to today's count."""

    try:
        tmp = _COUNT_FILE + ".tmp"

        with open(tmp, "w") as fh:
            json.dump(
                {
                    "date": _today(),
                    "count": _fires_today() + 1,
                },
                fh,
            )

        os.replace(tmp, _COUNT_FILE)

    except Exception:
        pass


# ---------------- strike calculation ----------------

def _counter_buy_offset(remaining_df):
    """
    Calculate the counter-buy strike offset.

    symbol -> active option strike and type
    price  -> price supplied in remaining_df

    ATM / ITM -> 0
    OTM       -> difference rounded to nearest 50
    """

    if remaining_df is None or remaining_df.empty:
        return None

    if not {"symbol", "price"}.issubset(remaining_df.columns):
        return None

    symbols = remaining_df["symbol"].astype(str).str.upper()

    # Extract only the final five strike digits before CE/PE.
    # Example: NIFTY26N0323000CE -> 23000CE.
    parsed = symbols.str.extract(r"(\d{5})(CE|PE)$")

    if parsed.isna().any().any():
        return None

    strikes = parsed[0].astype(int).unique()
    option_types = parsed[1].unique()

    if len(strikes) != 1 or len(option_types) != 1:
        return None

    strike = int(strikes[0])
    option_type = str(option_types[0])

    prices = pd.to_numeric(
        remaining_df["price"],
        errors="coerce",
    ).dropna()

    if prices.empty:
        return None

    spot = float(prices.iloc[0])

    if not pd.notna(spot) or spot <= 0:
        return None

    # Single diagnostic print.
    print(
        f"{Fore.CYAN}COUNTER-BUY | "
        f"SPOT: {spot:.2f} | "
        f"ACTIVE STRIKE: {strike} | "
        f"TYPE: {option_type}{Style.RESET_ALL}",
        flush=True,
    )

    step = STRIKE_STEP

    atm_strike = int(
        ((spot / step) + 0.5) // 1 * step
    )

    if strike == atm_strike:
        return 0

    if option_type == "CE" and strike < spot:
        return 0

    if option_type == "PE" and strike > spot:
        return 0

    difference = abs(strike - spot)

    return int(
        ((difference + step / 2) // step) * step
    )


# ---------------- main entry ----------------

def check_counter_leg(remaining_df):
    """
    remaining_df: rows still held after this cycle's target exits.

    Returns the name of the script fired, or None.
    """

    try:

        if remaining_df is None or remaining_df.empty:
            debug_log(
                "Counter check: no rows remaining after exits."
            )
            return None

        signal = str(
            remaining_df.iloc[0].get(
                EXIT_KEY_COLUMN,
                "NONE",
            )
        ).upper().strip()

        records = remaining_df[
            ["symbol", "qty"]
        ].to_dict("records")

        script_name = counter_leg_script(
            signal,
            records,
            CBUY_SCRIPTS,
        )

        if script_name is None:
            debug_log(
                f"Counter check: exit signal {signal} "
                "does not oppose exactly one held option side."
            )
            return None

        # ---------------- strike selection ----------------

        if EXECBUYPXY_USE_DYNAMIC_STRIKE:

            offset = _counter_buy_offset(remaining_df)

            if offset is None:
                print(
                    f"{Fore.YELLOW} ⚠ Counter-buy skipped: "
                    "could not safely calculate dynamic strike offset."
                )
                return None

        else:
            debug_log(
                "Simple Call Mode Active: using offset 0."
            )
            offset = 0

        # --------------------------------------------------

        held = "PE" if signal == "BULL" else "CE"
        counter = "PE" if held == "CE" else "CE"

        now = datetime.now(_IST).time()

        # ---------------- cooldown protection ----------------

        lock_key = f"CBUY|{script_name}"

        safety_cooldown = max(
            5.0,
            float(
                CBUY_LOCK_SECS
                if CBUY_LOCK_SECS is not None
                else 0
            ),
        )

        locked = _recent(
            _load_locks(),
            lock_key,
            safety_cooldown,
        )

        # Preserve existing counter-buy permission behaviour.
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
                f"Counter check: past {CBUY_CUTOFF}; "
                f"not firing {script_name}."
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
                    f"({CBUY_MAX_PER_DAY} launches); "
                    f"not firing {script_name}."
                )

            return None

        print(
            f"{Fore.YELLOW}⚠️ Exit signal ({signal}): "
            f"remaining {held} rows with NO {counter} leg."
        )

        if permission == "passive":

            print(
                f"{Fore.BLUE}{Style.BRIGHT}"
                f"ℹ️ [PASSIVE ALERT] "
                f"CBUY_ACTION=NO. Would fire "
                f"{script_name} with offset {offset}."
            )

            return None

        # ---------------- locate script ----------------

        path = _find_script(script_name)

        if not path:
            print(
                f"{Fore.RED} ❌ Counter script "
                f"{script_name} not found "
                "(searched the engine, system, PXY, and PATH locations)."
            )
            return None

        # ---------------- final offset ----------------

        # Pass calculated offset directly.
        # No weekday adjustment.
        # No signal-based offset.
        # No additional addition.

        final_offset = int(offset)

        # ---------------- launch ----------------

        _mark_lock(lock_key)
        _count_fire()

        subprocess.Popen(
            [
                "bash",
                path,
                str(final_offset),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        print(
            f"{Fore.MAGENTA}{Style.BRIGHT}"
            f" ⚡ FIRED COUNTER-BUY: "
            f"{script_name} {final_offset}"
        )

        return script_name

    except Exception as e:

        print(
            f"{Fore.RED} ❌ Counter-check error; "
            f"counter-buy NOT launched: {e}"
        )

        return None

