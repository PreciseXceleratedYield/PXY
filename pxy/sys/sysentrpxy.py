# ==================================================
# sysentrpxy.py  (3-LAYER EXECUTION ENGINE + TIME BLOCK)
# ==================================================

from sysmktpxy import get_signal
from syslhhlpxy import get_phase_direction
from datetime import datetime, time
import pytz


# ------------------------------
# CONFIG
# ------------------------------
TIMEZONE = "Asia/Kolkata"

BLOCK_START = time(9, 14, 0)
BLOCK_END   = time(9, 15, 49)


# ==================================================
def _map_entry_signal(entry_signal: str) -> str:

    if entry_signal == "BUY":
        return "ATMBUY"

    if entry_signal == "SELL":
        return "ATMSELL"

    return entry_signal


# ==================================================
def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    # ==================================================
    # 🥇 LAYER 0 — TIME BLOCK (HIGHEST PRIORITY)
    # ==================================================
    if BLOCK_START <= now <= BLOCK_END:
        return "NONE", "NONE"

    # ------------------------------
    # STRUCTURE ENGINE
    # ------------------------------
    phase, lhhl = get_phase_direction(df)

    # ------------------------------
    # SIGNAL ENGINE
    # ------------------------------
    entry_signal, _ = get_signal(df)

    # ==================================================
    # 🥇 LAYER 1 — ORB OVERRIDE
    # ==================================================
    if lhhl == "ORBUP":
        return "ATMBUY", "NONE"

    if lhhl == "ORBDOWN":
        return "ATMSELL", "NONE"

    # ==================================================
    # 🥈 LAYER 2 — TRANSITION FORCE MODE
    # ==================================================
    if lhhl in ("TRASUP", "NONEUP"):
        return "ATMBUY", "NONE"

    if lhhl in ("TRANSDOWN", "NONEDOWN"):
        return "ATMSELL", "NONE"

    # ==================================================
    # 🥉 LAYER 3 — NORMAL MODE
    # ==================================================

    base_entry = _map_entry_signal(entry_signal)

    if lhhl == "UP":
        if base_entry == "BUY":
            return "ATMBUY", "NONE"
        return base_entry, "NONE"

    if lhhl == "DOWN":
        if base_entry == "SELL":
            return "ATMSELL", "NONE"
        return base_entry, "NONE"

    if entry_signal in ("BULL", "BEAR", "NONE"):
        return entry_signal, "NONE"

    return base_entry, "NONE"
