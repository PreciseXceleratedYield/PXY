# ==================================================
# sysentrpxy.py (FINAL CLEAN + TIME + ST + ATR-SMA FILTER)
# ==================================================

from sysmktpxy import get_signal
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from sysatsmpxy import get_atr_sma
from sysbbospxy import get_bos

df = fetch_yf_data()

from datetime import datetime, time
import pytz

DEBUG = False

def debug_log(*args):
    if DEBUG:
        print(*args)

TIMEZONE = "Asia/Kolkata"

# -------------------- SWITCHES --------------------
USE_TIME_FILTER      = True
USE_MORNING_OVERRIDE = True
USE_FORCE_OTM        = True
USE_ST_FILTER        = True
USE_ATR_SMA          = False
USE_BOS              = True

# -------------------- TIME WINDOWS --------------------
NONE_START = time(9, 14, 0)
NONE_END   = time(9, 15, 59)

FORCE_OTM_START = time(9, 16, 0)
FORCE_OTM_END   = time(9, 25, 0)

MORNING_START = time(9, 15, 0)
MORNING_END   = time(10, 0, 0)


# -------------------- ENTRY MAPPING --------------------
def map_entry(sig, close=None, st=None, now=None):

    debug_log("🔵 map_entry INPUT:", sig, close, st, now)

    # -------- PHASE 1: FORCE OTM --------
    if USE_FORCE_OTM:
        if FORCE_OTM_START <= now <= FORCE_OTM_END:
            if sig == "BUY":
                return "OTMBUY"
            if sig == "SELL":
                return "OTMSELL"
            return sig

    # -------- PHASE 2: ST FILTER --------
    if sig == "BUY":
        signal = "ATMBUY"

        if USE_ST_FILTER:
            if close is not None and st is not None:
                if close < st:
                    signal = "NONE"

        return signal

    if sig == "SELL":
        signal = "ATMSELL"

        if USE_ST_FILTER:
            if close is not None and st is not None:
                if close > st:
                    signal = "NONE"

        return signal

    return sig


# -------------------- ATR SMA VALIDATION --------------------
def validate_with_sma(signal, close, sma_value):

    if not USE_ATR_SMA:
        return signal

    if sma_value is None:
        return "NONE"

    if signal in ["ATMBUY", "OTMBUY"]:
        if close < sma_value:
            return signal
        return "OTMBUY"

    if signal in ["ATMSELL", "OTMSELL"]:
        if close > sma_value:
            return signal
        return "OTMSELL"

    return signal


# -------------------- CORE --------------------
def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    debug_log("\n================ NEW RUN ================")
    debug_log("🕒 TIME:", now)

    # -------- PHASE 0: NONE --------
    if USE_TIME_FILTER:
        if NONE_START <= now <= NONE_END:
            return "NONE", "NONE"

    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    # ST
    if 'ST' not in df.columns:
        df = calculate_supertrend(df)

    last_st = df.iloc[-1]
    close = last_st['Close']
    st = last_st['ST'] if 'ST' in df.columns else close

    # -------------------- BASE SIGNAL --------------------
    entry_signal, exit_signal = get_signal()

    if entry_signal is None:
        entry_signal = "NONE"
        exit_signal = "NONE"

    # ==================================================
    # 🌅 MORNING OVERRIDE (NO LOGIC CHANGE — EARLY EXIT)
    # ==================================================
    if USE_MORNING_OVERRIDE:
        if MORNING_START <= now <= MORNING_END:

            if entry_signal == "BUY":
                return "OTMBUY", exit_signal

            elif entry_signal == "SELL":
                return "OTMSELL", exit_signal

            else:
                return "NONE", exit_signal

    # -------------------- NORMAL FLOW --------------------

    # ST MAPPING
    entry = map_entry(entry_signal, close, st, now)

    # ATR-SMA
    sma_data = get_atr_sma(df)
    sma_value = sma_data["atrsma"]

    last_sma = df.iloc[-2]
    close_sma = last_sma["Close"]

    entry = validate_with_sma(entry, close_sma, sma_value)

    # -------------------- BOS --------------------
    if USE_BOS:

        bos_signal = get_bos(df)

        # CASE ENGINE (UNCHANGED)
        if entry == "BULL" and bos_signal == "RBUY":
            entry = "OTMBUY"

        elif entry == "BEAR" and bos_signal == "RSELL":
            entry = "OTMSELL"

        elif entry == "NONE" and bos_signal == "RBUY":
            entry = "OTMBUY"

        elif entry == "NONE" and bos_signal == "RSELL":
            entry = "OTMSELL"

    return entry, exit_signal


# -------------------- TEST --------------------
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
