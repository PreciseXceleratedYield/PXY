# ==================================================
# sysentrpxy.py (FINAL STABLE ENGINE)
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


FORCE_UP = {"ORBUP", "TRASUP", "NONEUP"}
FORCE_DOWN = {"ORBDOWN", "TRANSDOWN", "NONEDOWN"}


# ------------------------------
# ENTRY MAP
# ------------------------------
def _map_entry(signal):
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
    # DATA SOURCE
    # ------------------------------
    if df is None:
        df = fetch_yf_data()

    # 🔥 FIX: NORMALIZE COLUMN FORMAT
    df.columns = [c.title() for c in df.columns]

    # ------------------------------
    # LHHL ENGINE
    # ------------------------------
    phase, lhhl = get_phase_direction(df)

    print("[DEBUG] RAW LHHL:", repr(lhhl))
    lhhl_clean = str(lhhl).strip().upper()
    print("[DEBUG] CLEAN LHHL:", lhhl_clean)

    # ------------------------------
    # MARKET SIGNAL ENGINE
    # ------------------------------
    entry_signal, exit_signal = get_signal(df)

    print("[DEBUG] ENTRY SIGNAL:", entry_signal)
    print("[DEBUG] EXIT SIGNAL :", exit_signal)

    base_entry = _map_entry(entry_signal)
    print("[DEBUG] BASE ENTRY:", base_entry)

    # ------------------------------
    # FORCE LAYER
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
        if base_entry == "BUY":
            return "ATMBUY", exit_signal
        return base_entry, exit_signal

    if lhhl_clean == "DOWN":
        if base_entry == "SELL":
            return "ATMSELL", exit_signal
        return base_entry, exit_signal

    return base_entry, exit_signal


# ==================================================
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
