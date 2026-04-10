# ==================================================
# sysentrpxy.py (FINAL CLEAN + TIME + ST LOGIC)
# ==================================================

from sysmktpxy import get_signal
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend

from datetime import datetime, time
import pytz

DEBUG = False

def debug_log(*args):
    if DEBUG:
        print(*args)


TIMEZONE = "Asia/Kolkata"

# -------------------- TIME WINDOWS --------------------
NONE_START = time(9, 14, 0)
NONE_END   = time(9, 15, 59)

FORCE_OTM_START = time(9, 16, 0)
FORCE_OTM_END   = time(9, 25, 0)


# -------------------- ENTRY MAPPING --------------------
def map_entry(sig, close=None, st=None, now=None):

    # -------- PHASE 1: FORCE OTM --------
    if FORCE_OTM_START <= now <= FORCE_OTM_END:
        if sig == "BUY":
            return "OTMBUY"
        if sig == "SELL":
            return "OTMSELL"
        return sig

    # -------- PHASE 2: ST FILTER --------
    if sig == "BUY":
        signal = "ATMBUY"

        if close is not None and st is not None:
            if close < st:
                signal = "OTMBUY"

        return signal

    if sig == "SELL":
        signal = "ATMSELL"

        if close is not None and st is not None:
            if close > st:
                signal = "OTMSELL"

        return signal

    return sig


# -------------------- CORE --------------------
def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    # -------- PHASE 0: NONE --------
    if NONE_START <= now <= NONE_END:
        return "NONE", "NONE"

    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    # Ensure ST exists
    if 'ST' not in df.columns:
        df = calculate_supertrend(df)

    last = df.iloc[-1]
    close = last['Close']
    st = last['ST'] if 'ST' in df.columns else close

    entry_signal, exit_signal = get_signal()

    if entry_signal is None:
        entry_signal = "NONE"
        exit_signal = "NONE"

    # Apply mapping with time + ST
    entry = map_entry(entry_signal, close, st, now)
    print(f"CLOSE: {close:.2f} | ST: {st:.2f}")
    return entry, exit_signal


# -------------------- TEST --------------------
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
    
