# ==================================================
# sysentrpxy.py  (FINAL EXECUTION ENGINE)
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
    # 🥇 LAYER 0 — TIME BLOCK
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
    entry_signal, exit_signal = get_signal(df)

    # ==================================================
    # 🥇 LAYER 1 — ORB OVERRIDE
    # ==================================================
    if lhhl == "ORBUP":
        return "ATMBUY", exit_signal

    if lhhl == "ORBDOWN":
        return "ATMSELL", exit_signal

    # ==================================================
    # 🥈 LAYER 2 — TRANSITION FORCE MODE
    # ==================================================
    if lhhl in ("TRASUP", "NONEUP"):
        return "ATMBUY", exit_signal

    if lhhl in ("TRANSDOWN", "NONEDOWN"):
        return "ATMSELL", exit_signal

    # ==================================================
    # 🥉 LAYER 3 — NORMAL MODE
    # ==================================================

    base_entry = _map_entry_signal(entry_signal)

    if lhhl == "UP":
        if base_entry == "BUY":
            return "ATMBUY", exit_signal
        return base_entry, exit_signal

    if lhhl == "DOWN":
        if base_entry == "SELL":
            return "ATMSELL", exit_signal
        return base_entry, exit_signal

    if entry_signal in ("BULL", "BEAR", "NONE"):
        return entry_signal, exit_signal

    return base_entry, exit_signal


# ==================================================
# MAIN RUN
# ==================================================
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print(f"ENTRY  : {entry}")
    print(f"EXIT   : {exit_signal}")
