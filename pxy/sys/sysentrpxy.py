# ==================================================
# sysentrpxy.py (FINAL - FORCE + DATA SYNC FIXED)
# ==================================================

from sysmktpxy import get_signal
from syslhhlpxy import get_phase_direction
from sysdtafpxy import fetch_yf_data
from datetime import datetime, time
import pytz


TIMEZONE = "Asia/Kolkata"

BLOCK_START = time(9, 14, 0)
BLOCK_END   = time(9, 15, 49)


FORCE_UP = {"ORBUP", "TRASUP", "NONEUP"}
FORCE_DOWN = {"ORBDOWN", "TRANSDOWN", "NONEDOWN"}


def _map_entry(signal):
    if signal == "BUY":
        return "ATMBUY"
    if signal == "SELL":
        return "ATMSELL"
    return signal


def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    print("\n================ DEBUG START ================")
    print("[DEBUG] TIME:", now)

    # -----------------------------
    # TIME BLOCK
    # -----------------------------
    if BLOCK_START <= now <= BLOCK_END:
        print("[DEBUG] TIME BLOCK → NONE")
        return "NONE", "NONE"

    # -----------------------------
    # SINGLE SOURCE OF TRUTH (FIX)
    # -----------------------------
    if df is None:
        df = fetch_yf_data()

    # -----------------------------
    # LHHL ENGINE (SAME DF NOW)
    # -----------------------------
    phase, lhhl = get_phase_direction(df)

    print("[DEBUG] RAW LHHL:", repr(lhhl))
    lhhl_clean = lhhl.strip().upper()
    print("[DEBUG] CLEAN LHHL:", lhhl_clean)

    # -----------------------------
    # FORCE LAYER
    # -----------------------------
    if lhhl_clean in FORCE_UP:
        print("[DEBUG] FORCE → ATMBUY")
        print("===========================================\n")
        return "ATMBUY", "NONE"

    if lhhl_clean in FORCE_DOWN:
        print("[DEBUG] FORCE → ATMSELL")
        print("===========================================\n")
        return "ATMSELL", "NONE"

    print("[DEBUG] NO FORCE → SIGNAL MODE")

    # -----------------------------
    # NORMAL MODE
    # -----------------------------
    entry, exit_signal = get_signal(df)

    print("[DEBUG] ENTRY:", entry)
    print("[DEBUG] EXIT :", exit_signal)

    base = _map_entry(entry)

    print("[DEBUG] BASE:", base)

    if lhhl_clean == "UP":
        if base == "BUY":
            return "ATMBUY", exit_signal
        return base, exit_signal

    if lhhl_clean == "DOWN":
        if base == "SELL":
            return "ATMSELL", exit_signal
        return base, exit_signal

    return base, exit_signal


if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
