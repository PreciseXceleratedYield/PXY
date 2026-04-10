# ==================================================
# sysentrpxy.py  (STATELESS FORCE-FIRST ENGINE)
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
FORCE_UP = {"ORBUP", "TRASUP", "NONEUP"}
FORCE_DOWN = {"ORBDOWN", "TRANSDOWN", "NONEDOWN"}


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
    # 🥇 LAYER 0 — TIME BLOCK (HARD STOP)
    # ==================================================
    if BLOCK_START <= now <= BLOCK_END:
        return "NONE", "NONE"

    # ==================================================
    # 🧠 LHHL STATE (PURE COMPUTATION)
    # ==================================================
    _, lhhl = get_phase_direction(df)

    # ==================================================
    # 🥇 LAYER 1 — FORCE MODE (NO SIGNAL ENGINE)
    # ==================================================
    if lhhl in FORCE_UP:
        return "ATMBUY", "NONE"

    if lhhl in FORCE_DOWN:
        return "ATMSELL", "NONE"

    # ==================================================
    # 🥈 LAYER 2 — NORMAL SIGNAL MODE
    # ==================================================
    entry_signal, exit_signal = get_signal(df)

    base_entry = _map_entry_signal(entry_signal)

    if lhhl == "UP":
        if base_entry == "BUY":
            return "ATMBUY", exit_signal
        return base_entry, exit_signal

    if lhhl == "DOWN":
        if base_entry == "SELL":
            return "ATMSELL", exit_signal
        return base_entry, exit_signal

    # ==================================================
    # 🟡 PASS THROUGH
    # ==================================================
    return base_entry, exit_signal


# ==================================================
# MAIN
# ==================================================
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print(f"ENTRY  : {entry}")
    print(f"EXIT   : {exit_signal}")
