# ==================================================
# sysentrpxy.py (PRODUCTION FINAL ENGINE)
# ==================================================

from sysmktpxy import get_signal
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos
from syssmapxy import get_sma

from datetime import datetime, time
import pytz

TIMEZONE = "Asia/Kolkata"

# -------------------- DEBUG SWITCH --------------------
DEBUG = True   # 🔴 GLOBAL SWITCH

def dprint(label, value=""):
    if DEBUG:
        msg = f"{str(label):<20} {str(value):<22}"
        print(msg[:42])


# -------------------- MORNING WINDOW --------------------
MORNING_START = time(9, 16, 0)
MORNING_END   = time(9, 25, 0)


# ==================================================
# CORE ENGINE
# ==================================================
def get_entry_signal(df=None):

    now = datetime.now(pytz.timezone(TIMEZONE)).time()
    dprint("CURRENT TIME", now)

    # ==================================================
    # 🕒 1. MORNING OVERRIDE (RAW MODE)
    # ==================================================
    if MORNING_START <= now <= MORNING_END:

        signal, exit_signal = get_signal()
        dprint("MORNING SIGNAL", signal)
        dprint("EXIT SIGNAL", exit_signal)

        if signal in ["BUY", "BULL"]:
            dprint("RETURN", "OTMBUY")
            return "OTMBUY", exit_signal

        if signal in ["SELL", "BEAR"]:
            dprint("RETURN", "OTMSELL")
            return "OTMSELL", exit_signal

        dprint("RETURN", "NONE")
        return "NONE", exit_signal

    # ==================================================
    # 🧠 DATA PREPARATION
    # ==================================================
    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")
        dprint("FETCH DATA", "5d 1m")

    if df is None or len(df) < 3:
        dprint("DATA STATUS", "INSUFFICIENT")
        return "NONE", "NONE"

    if 'ST' not in df.columns:
        df = calculate_supertrend(df)
        dprint("SUPERTREND", "CALCULATED")

    last = df.iloc[-1]
    st_trend = last['ST_Trend']

    dprint("ST TREND", st_trend)

    signal, exit_signal = get_signal()
    dprint("SIGNAL", signal)
    dprint("EXIT", exit_signal)

    if signal is None:
        dprint("RETURN", "NONE")
        return "NONE", "NONE"

    bos = get_bos(df)
    dprint("BOS", bos)

    # ==================================================
    # ⚡ 2. BOS BREAKOUT MODE (HIGHEST AFTER MORNING)
    # ==================================================
    if bos == "BUY" and st_trend == "DOWN":
        dprint("MODE", "BOS BUY REVERSAL")
        return "OTMBUY", exit_signal

    if bos == "SELL" and st_trend == "UP":
        dprint("MODE", "BOS SELL REVERSAL")
        return "OTMSELL", exit_signal

    # ==================================================
    # 🔁 3. COUNTER MODE
    # ==================================================
    sma = get_sma(df, period=9)
    print(sma)
    if signal == "BUY" and st_trend == "DOWN" and bos == "BUY":
        dprint("MODE", "COUNTER BUY")
        return "OTMBUY", exit_signal

    if signal == "SELL" and st_trend == "UP" and bos == "SELL":
        dprint("MODE", "COUNTER SELL")
        return "OTMSELL", exit_signal

    # ==================================================
    # 🟢 4. TREND MODE
    # ==================================================
    if signal == "BUY" and st_trend == "UP":
        dprint("MODE", "TREND BUY")
        return "ATMBUY", exit_signal

    if signal == "SELL" and st_trend == "DOWN":
        dprint("MODE", "TREND SELL")
        return "ATMSELL", exit_signal

    # ==================================================
    # ❌ 5. NO TRADE
    # ==================================================
    dprint("FINAL", signal)
    return signal, exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
