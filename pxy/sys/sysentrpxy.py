# ==================================================
# sysentrpxy.py
# ==================================================

from sysmktpxy import get_signal
from datetime import datetime, time
import pytz  # to handle IST timezone

# ------------------------------
# CONFIG: Blocked Time Window (IST)
# ------------------------------
BLOCK_START = time(9, 14)  # Start of block
BLOCK_END   = time(9, 15)  # End of block
TIMEZONE    = "Asia/Kolkata"  # IST

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
        # Check for blocked time window
        # ------------------------
        tz = pytz.timezone(TIMEZONE)
        now = datetime.now(tz).time()

        if BLOCK_START <= now <= BLOCK_END:
            return "NONE", "NONE"

        # ------------------------
        # Normal signal processing
        # ------------------------
        entry_signal, exit_signal = get_signal(df)
        final_entry = _map_entry_signal(entry_signal)
        final_exit = exit_signal

        return final_entry, final_exit

    except Exception:
        return "NONE", "NONE"
