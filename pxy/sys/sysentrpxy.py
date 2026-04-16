# ==================================================
# sysentrpxy.py (PRODUCTION FINAL ENGINE)
# ==================================================

from sysmktpxy import get_signal
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos

from datetime import datetime, time
import pytz

TIMEZONE = "Asia/Kolkata"

# -------------------- MORNING WINDOW --------------------
MORNING_START = time(9, 16, 0)
MORNING_END   = time(9, 25, 0)


# ==================================================
# CORE ENGINE
# ==================================================
def get_entry_signal(df=None):

    now = datetime.now(pytz.timezone(TIMEZONE)).time()

    # ==================================================
    # 🕒 1. MORNING OVERRIDE (RAW MODE)
    # ==================================================
    if MORNING_START <= now <= MORNING_END:

        signal, exit_signal = get_signal()

        if signal in ["BUY", "BULL"]:
            return "OTMBUY", exit_signal

        if signal in ["SELL", "BEAR"]:
            return "OTMSELL", exit_signal

        return "NONE", exit_signal

    # ==================================================
    # 🧠 DATA PREPARATION
    # ==================================================
    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    if 'ST' not in df.columns:
        df = calculate_supertrend(df)

    last = df.iloc[-1]
    st_trend = last['ST_Trend']

    signal, exit_signal = get_signal()
    if signal is None:
        return "NONE", "NONE"

    bos = get_bos(df)

    # ==================================================
    # ⚡ 2. BOS BREAKOUT MODE (HIGHEST AFTER MORNING)
    # ==================================================
    # BOS only matters when it OPPOSES ST
    if bos == "BUY" and st_trend == "DOWN":
        return "OTMBUY", exit_signal

    if bos == "SELL" and st_trend == "UP":
        return "OTMSELL", exit_signal

    # ==================================================
    # 🔁 3. COUNTER MODE (Signal + BOS confirms against ST)
    # ==================================================
    if signal == "BUY" and st_trend == "DOWN" and bos == "BUY":
        return "OTMBUY", exit_signal

    if signal == "SELL" and st_trend == "UP" and bos == "SELL":
        return "OTMSELL", exit_signal

    # ==================================================
    # 🟢 4. TREND MODE (Signal + ST alignment)
    # ==================================================
    if signal == "BUY" and st_trend == "UP":
        return "ATMBUY", exit_signal

    if signal == "SELL" and st_trend == "DOWN":
        return "ATMSELL", exit_signal

    # ==================================================
    # ❌ 5. NO TRADE
    # ==================================================
    return "NONE", exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
