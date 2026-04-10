# ==================================================
# sysentrpxy.py (FINAL CLEAN VERSION)
# ==================================================

from sysmktpxy import get_signal
from sysdtafpxy import fetch_yf_data
from datetime import datetime, time
import pytz

DEBUG = False

def debug_log(*args):
    if DEBUG:
        print(*args)


TIMEZONE = "Asia/Kolkata"

# ✅ ONLY FIRST 2 MIN BLOCK
NONE_START = time(9, 14, 0)
NONE_END   = time(9, 15, 59)


def map_entry(sig):
    if sig == "BUY":
        return "ATMBUY"
    if sig == "SELL":
        return "ATMSELL"
    return sig


def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    # TIME BLOCK ONLY HERE
    if NONE_START <= now <= NONE_END:
        return "NONE", "NONE"

    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    entry_signal, exit_signal = get_signal()

    if entry_signal is None:
        entry_signal = "NONE"
        exit_signal = "NONE"

    entry = map_entry(entry_signal)

    # EXIT = RAW ENTRY SIGNAL
    return entry, exit_signal


if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
