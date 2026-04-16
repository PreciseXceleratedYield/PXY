# ==================================================
# sysentrpxy.py (FINAL - MULLU + ST SYSTEM)
# ==================================================

from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from sysexitpxy import detect_raw_direction

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


# -------------------- CORE --------------------
def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    debug_log("\n================ NEW RUN ================")
    debug_log("🕒 TIME:", now)

    # -------- NONE WINDOW --------
    if NONE_START <= now <= NONE_END:
        return "NONE", "NONE"

    # -------- DATA --------
    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    # -------- SUPERTREND --------
    if 'ST' not in df.columns:
        df = calculate_supertrend(df)

    last_row = df.iloc[-1]
    close = last_row['Close']
    st = last_row['ST'] if 'ST' in df.columns else close

    # -------- MULLU --------
    price, direction = detect_raw_direction(df)

    debug_log("📌 CLOSE:", close, "ST:", st, "DIR:", direction)

    # ==================================================
    # 🔥 PHASE 1: MULLU ONLY (OPEN)
    # ==================================================
    if FORCE_OTM_START <= now <= FORCE_OTM_END:
        debug_log("⏱ MULLU MODE ACTIVE")

        if direction == "UP":
            entry = "OTMBUY"
        elif direction == "DOWN":
            entry = "OTMSELL"
        else:
            entry = "NONE"

        return entry, entry

    # ==================================================
    # 🔥 PHASE 2: MULLU + ST
    # ==================================================
    if direction == "UP":
        if close > st:
            entry = "ATMBUY"
        else:
            entry = "OTMBUY"

    elif direction == "DOWN":
        if close < st:
            entry = "ATMSELL"
        else:
            entry = "OTMSELL"

    else:
        entry = "NONE"

    debug_log("🏁 FINAL ENTRY:", entry)

    return entry, entry


# -------------------- TEST --------------------
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
