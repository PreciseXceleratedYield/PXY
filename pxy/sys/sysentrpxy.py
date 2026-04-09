# ==================================================
# sysentrpxy.py
# ==================================================

from sysmktpxy import get_signal
from datetime import datetime, time
import pytz  # to handle IST timezone

# ------------------------------
# CONFIG: Special Time Windows (IST)
# ------------------------------
TIMEZONE = "Asia/Kolkata"  # IST

# Blocked period: return NONE
BLOCK_NONE_START = time(9, 14)
BLOCK_NONE_END   = time(9, 15, 59)  # inclusive of 9:15

# Special period: ALLBUY for entry only
BLOCK_ALLBUY_START = time(9, 16)
BLOCK_ALLBUY_END   = time(9, 17, 59)  # inclusive of 9:17

# ------------------------------
# ENTRY Mapping
# ------------------------------
def _map_entry_signal(entry_signal: str) -> str:
    if entry_signal == "BUY":
        return "ATMBUY"
    elif entry_signal == "SELL":
        return "ATMSELL"
    elif entry_signal in ("BULL", "BEAR"):
        return entry_signal
    else:
        return "NONE"

# ------------------------------
# MAIN FUNCTION
# ------------------------------
def get_entry_signal(df=None):
    try:
        # ------------------------
        # Current time in IST
        # ------------------------
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz).time()

        # ------------------------
        # Check for NONE window
        # ------------------------
        if BLOCK_NONE_START <= now <= BLOCK_NONE_END:
            return "NONE", "NONE"

        # ------------------------
        # Normal signal processing
        # ------------------------
        entry_signal, exit_signal = get_signal(df)
        final_exit = exit_signal  # exit always normal

        # ------------------------
        # Check for ALLBUY window (entry only)
        # ------------------------
        if BLOCK_ALLBUY_START <= now <= BLOCK_ALLBUY_END:
            final_entry = "SBEULYL"
        else:
            final_entry = _map_entry_signal(entry_signal)

        return final_entry, final_exit

    except Exception:
        return "NONE", "NONE"
