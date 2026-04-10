# ==================================================
# sysentrpxy.py (FINAL PRODUCTION STABLE)
# ==================================================

from sysmktpxy import get_signal
from syslhhlpxy import get_phase_direction
from sysdtafpxy import fetch_yf_data
from datetime import datetime, time
import pytz


# ------------------------------
# CONFIG
# ------------------------------
TIMEZONE = "Asia/Kolkata"

BLOCK_NONE_START = time(9, 14)
BLOCK_NONE_END   = time(9, 15, 59)


# LHHL FORCE RULES
FORCE_UP = {"ORBUP", "TRASUP", "NONEUP"}
FORCE_DOWN = {"ORBDOWN", "TRANSDOWN", "NONEDOWN"}


# ------------------------------
# ENTRY MAPPING
# ------------------------------
def map_entry(signal):
    if signal == "BUY":
        return "ATMBUY"
    if signal == "SELL":
        return "ATMSELL"
    return signal


# ==================================================
# MAIN ENGINE
# ==================================================
def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    print("\n================ DEBUG START ================")
    print("[DEBUG] TIME:", now)

    # ------------------------------
    # TIME BLOCK
    # ------------------------------
    if BLOCK_NONE_START <= now <= BLOCK_NONE_END:
        return "NONE", "NONE"

    # ------------------------------
    # DATA FETCH
    # ------------------------------
    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    # 🔥 CRITICAL FIX: isolate dataframe
    df = df.copy()

    print("[DEBUG] DF READY:", df.shape)

    # ------------------------------
    # LHHL ENGINE
    # ------------------------------
    phase, lhhl = get_phase_direction(df)

    lhhl_clean = str(lhhl).strip().upper()

    print("[DEBUG] RAW LHHL:", lhhl_clean)

    # ------------------------------
    # MARKET SIGNAL ENGINE
    # ------------------------------
    entry_signal, exit_signal = get_signal(df)

    print("[DEBUG] ENTRY SIGNAL:", entry_signal)
    print("[DEBUG] EXIT SIGNAL :", exit_signal)

    base_entry = map_entry(entry_signal)
    print("[DEBUG] BASE ENTRY:", base_entry)

    # ------------------------------
    # FORCE OVERRIDE (HIGHEST PRIORITY)
    # ------------------------------
    if lhhl_clean in FORCE_UP:
        print("[DEBUG] FORCE → ATMBUY")
        print("===========================================\n")
        return "ATMBUY", exit_signal

    if lhhl_clean in FORCE_DOWN:
        print("[DEBUG] FORCE → ATMSELL")
        print("===========================================\n")
        return "ATMSELL", exit_signal

    print("[DEBUG] NO FORCE → NORMAL MODE")

    # ------------------------------
    # NORMAL MODE
    # ------------------------------
    if lhhl_clean == "UP":
        return ("ATMBUY" if base_entry == "BUY" else base_entry), exit_signal

    if lhhl_clean == "DOWN":
        return ("ATMSELL" if base_entry == "SELL" else base_entry), exit_signal

    # ------------------------------
    # DEFAULT FALLBACK
    # ------------------------------
    return base_entry, exit_signal


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
