# ==================================================
# sysentrpxy.py (FINAL CLEAN + TIME + ST + ATR-SMA FILTER)
# ==================================================

from sysmktpxy import get_signal
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend
from sysatsmpxy import get_atr_sma   # ✅ NEW IMPORT
from sysbbospxy import get_bos

df = fetch_yf_data()

from datetime import datetime, time
import pytz

DEBUG = True   # ENABLED

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

    debug_log("🔵 map_entry INPUT:", sig, close, st, now)

    # -------- PHASE 1: FORCE OTM --------
    if FORCE_OTM_START <= now <= FORCE_OTM_END:
        debug_log("⏱ FORCE OTM ACTIVE")

        if sig == "BUY":
            debug_log("➡ RETURN OTMBUY")
            return "OTMBUY"
        if sig == "SELL":
            debug_log("➡ RETURN OTMSELL")
            return "OTMSELL"

        debug_log("➡ RETURN SAME SIG:", sig)
        return sig

    # -------- PHASE 2: ST FILTER --------
    if sig == "BUY":
        signal = "ATMBUY"
        debug_log("BUY → initial:", signal)

        if close is not None and st is not None:
            if close < st:
                debug_log("❌ close < st → NONE")
                signal = "NONE"

        debug_log("➡ RETURN:", signal)
        return signal

    if sig == "SELL":
        signal = "ATMSELL"
        debug_log("SELL → initial:", signal)

        if close is not None and st is not None:
            if close > st:
                debug_log("❌ close > st → NONE")
                signal = "NONE"

        debug_log("➡ RETURN:", signal)
        return signal

    debug_log("➡ DEFAULT RETURN:", sig)
    return sig


# -------------------- ATR SMA VALIDATION --------------------
def validate_with_sma(signal, close, sma_value):

    debug_log("🟡 validate_with_sma INPUT:", signal, close, sma_value)

    if sma_value is None:
        debug_log("⚠ SMA NONE → RETURN NONE")
        return "NONE"

    if signal in ["ATMBUY", "OTMBUY"]:
        if close < sma_value:
            debug_log("BUY VALID (close < sma)")
            return signal
        debug_log("BUY FAIL → OTMBUY")
        return "OTMBUY"

    if signal in ["ATMSELL", "OTMSELL"]:
        if close > sma_value:
            debug_log("SELL VALID (close > sma)")
            return signal
        debug_log("SELL FAIL → OTMSELL")
        return "OTMSELL"

    debug_log("➡ RETURN RAW:", signal)
    return signal


# -------------------- CORE --------------------
def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    debug_log("\n================ NEW RUN ================")
    debug_log("🕒 TIME:", now)

    # -------- PHASE 0: NONE --------
    if NONE_START <= now <= NONE_END:
        debug_log("⛔ NONE WINDOW ACTIVE")
        return "NONE", "NONE"

    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")
        debug_log("📊 DATA FETCHED:", len(df) if df is not None else 0)

    if df is None or len(df) < 3:
        debug_log("❌ NOT ENOUGH DATA")
        return "NONE", "NONE"

    # Ensure ST exists
    if 'ST' not in df.columns:
        debug_log("⚙ CALCULATING SUPERTRAND")
        df = calculate_supertrend(df)

    last_st = df.iloc[-1]
    close = last_st['Close']
    st = last_st['ST'] if 'ST' in df.columns else close

    debug_log("📌 CLOSE:", close, "ST:", st)

    # -------------------- BASE SIGNAL --------------------
    entry_signal, exit_signal = get_signal()
    debug_log("📡 RAW SIGNAL:", entry_signal, exit_signal)

    if entry_signal is None:
        entry_signal = "NONE"
        exit_signal = "NONE"

    # -------------------- ST MAPPING --------------------
    entry = map_entry(entry_signal, close, st, now)
    debug_log("🧠 AFTER MAP_ENTRY:", entry)

    # -------------------- ATR-SMA --------------------
    sma_data = get_atr_sma(df)
    sma_value = sma_data["atrsma"]
    debug_log("📉 ATR-SMA VALUE:", sma_value)

    last_sma = df.iloc[-2]
    close_sma = last_sma["Close"]

    entry = validate_with_sma(entry, close_sma, sma_value)
    debug_log("📊 AFTER SMA FILTER:", entry)

    # -------------------- BOS --------------------
    bos_signal = get_bos(df)
    debug_log("🧩 BOS SIGNAL:", bos_signal)

    # CASE ENGINE
    if entry == "BULL" and bos_signal == "RBUY":
        debug_log("CASE 1 HIT")
        entry = "OTMBUY"

    elif entry == "BEAR" and bos_signal == "RSELL":
        debug_log("CASE 2 HIT")
        entry = "OTMSELL"

    elif entry == "NONE" and bos_signal == "RBUY":
        debug_log("CASE 3 HIT")
        entry = "OTMBUY"

    elif entry == "NONE" and bos_signal == "RSELL":
        debug_log("CASE 4 HIT")
        entry = "OTMSELL"

    elif bos_signal == "NONE":
        debug_log("CASE 5 PASS")

    debug_log("🏁 FINAL ENTRY:", entry)

    return entry, exit_signal


# -------------------- TEST --------------------
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
