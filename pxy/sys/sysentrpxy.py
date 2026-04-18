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

# -------------------- GLOBAL MODE SWITCH --------------------
MODE = "RAW"   # "TREND" | "RAW"
DEBUG = False


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
    # 🧪 RAW MODE (NO INDICATORS, ONLY CONFIRMATION LOGIC)
    # ==================================================
    if MODE == "RAW":

        signal, exit_signal = get_signal()
        dprint("RAW SIGNAL", signal)
        dprint("RAW EXIT", exit_signal)

        # SAFE DF fallback
        if df is None:
            df = fetch_yf_data(period="5d", interval="1m")

        if df is None or len(df) < 3:
            return signal, exit_signal   # fallback RAW

        last = df.iloc[-1]
        bos = get_bos(df)
        st_trend = last.get('ST_Trend', "NONE")

        dprint("RAW BOS", bos)
        dprint("RAW ST", st_trend)

        # ==================================================
        # 🕒 MORNING (PURE RAW ENTRY)
        # ==================================================
        if MORNING_START <= now <= MORNING_END:

            if exit_signal in ["BUY", "BULL"]:
                return "OTMBUY", exit_signal
            
            if exit_signal in ["SELL", "BEAR"]:
                return "OTMSELL", exit_signal
            
            return signal, exit_signal


        # ==================================================
        # 🧠 AFTER MORNING (RAW + ST + BOS LOGIC)
        # ==================================================

        if signal == "BUY":

            # STRONG CONFIRMATION → ATM
            if st_trend == "UP" and bos in ["BUY", "UP"]:
                return "ATMBUY", exit_signal

            # WEAK CONFIRMATION → OTM
            if st_trend == "UP" or bos in ["BUY", "UP"]:
                return "OTMBUY", exit_signal

            # NO CONFIRMATION → RAW CONTINUES
            return signal, exit_signal


        if signal == "SELL":

            # STRONG CONFIRMATION → ATM
            if st_trend == "DOWN" and bos in ["SELL", "DOWN"]:
                return "ATMSELL", exit_signal

            # WEAK CONFIRMATION → OTM
            if st_trend == "DOWN" or bos in ["SELL", "DOWN"]:
                return "OTMSELL", exit_signal

            # NO CONFIRMATION → RAW CONTINUES
            return signal, exit_signal


        return signal, exit_signal


    # ==================================================
    # 🧠 TREND MODE (UPDATED - MORNING SYNCED WITH RAW STYLE)
    # ==================================================
    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")
        dprint("FETCH DATA", "5d 1m")
    
    if df is None or len(df) < 3:
        return "NONE", "NONE"
    
    # -------------------- INDICATORS --------------------
    if 'ST' not in df.columns:
        df = calculate_supertrend(df)
        dprint("SUPERTREND", "CALCULATED")
    
    last = df.iloc[-1]
    st_trend = last['ST_Trend']
    
    signal, exit_signal = get_signal()
    
    if signal is None:
        return "NONE", "NONE"
    
    bos = get_bos(df)
    
    sma_result = get_sma(df, period=9)
    sma_status = sma_result["status"]
    
    # ==================================================
    # 🕒 MORNING WINDOW (TREND MODE FIXED)
    # ==================================================
    now = datetime.now(pytz.timezone(TIMEZONE)).time()
    
    # ==================================================
    if MORNING_START <= now <= MORNING_END:

        if exit_signal in ["BUY", "BULL"]:
            return "OTMBUY", exit_signal
            
        if exit_signal in ["SELL", "BEAR"]:
            return "OTMSELL", exit_signal
            
        return signal, exit_signal

    
    
    # ==================================================
    # ⚡ BOS BREAKOUT MODE
    # ==================================================
    if bos == "BUY" and st_trend == "DOWN":
        return "OTMBUY", exit_signal
    
    if bos == "SELL" and st_trend == "UP":
        return "OTMSELL", exit_signal
    
    
    # ==================================================
    # 🔁 COUNTER MODE
    # ==================================================
    if signal == "BUY" and st_trend == "DOWN" and sma_status == "UP":
        return "OTMBUY", exit_signal
    
    if signal == "SELL" and st_trend == "UP" and sma_status == "DOWN":
        return "OTMSELL", exit_signal
    
    
    # ==================================================
    # 🟢 TREND MODE
    # ==================================================
    if signal == "BUY" and st_trend == "UP":
        return "ATMBUY", exit_signal
    
    if signal == "SELL" and st_trend == "DOWN":
        return "ATMSELL", exit_signal
    
    return signal, exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
