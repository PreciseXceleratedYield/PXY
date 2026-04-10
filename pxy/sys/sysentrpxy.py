# ==================================================
# sysentrpxy.py (PRODUCTION FINAL FIXED)
# ==================================================

from sysmktpxy import get_signal
from syslhhlpxy import get_phase_direction
from sysdtafpxy import fetch_yf_data
from datetime import datetime, time
import pytz

# ------------------------------
# GLOBAL DEBUG SWITCH
# ------------------------------
DEBUG = False


def debug_log(*args):
    if DEBUG:
        print(*args)


# ------------------------------
# CONFIG
# ------------------------------
TIMEZONE = "Asia/Kolkata"

BLOCK_NONE_START = time(9, 14)
BLOCK_NONE_END   = time(9, 15, 59)

FORCE_UP = {"ORBUP", "TRASUP", "NONEUP"}
FORCE_DOWN = {"ORBDOWN", "TRANSDOWN", "NONEDOWN"}


# ------------------------------
# ENTRY MAPPING
# ------------------------------
def map_entry(sig):
    if sig == "BUY":
        return "ATMBUY"
    if sig == "SELL":
        return "ATMSELL"
    return sig


# ==================================================
# MAIN ENGINE
# ==================================================
def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    debug_log("\n================ DEBUG START ================")
    debug_log("[DEBUG] TIME:", now)

    # ------------------------------
    # TIME BLOCK
    # ------------------------------
    if BLOCK_NONE_START <= now <= BLOCK_NONE_END:
        return "NONE", "NONE"

    # ------------------------------
    # FETCH DATA
    # ------------------------------
    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    df = df.copy()

    debug_log("[DEBUG] DF READY:", df.shape)

    # ------------------------------
    # LHHL ENGINE
    # ------------------------------
    phase, lhhl = get_phase_direction(df)

    lhhl_clean = str(lhhl).strip().upper()
    debug_log("[DEBUG] RAW LHHL:", lhhl_clean)

    # ------------------------------
    # MARKET SIGNAL ENGINE
    # ------------------------------
    entry_signal, exit_signal = get_signal(df)

    debug_log("[DEBUG] RAW ENTRY SIGNAL:", entry_signal)
    debug_log("[DEBUG] RAW EXIT SIGNAL :", exit_signal)

    # 🔥 STORE ORIGINAL ENTRY FOR EXIT (IMPORTANT FIX)
    raw_entry_signal = entry_signal

    # ------------------------------
    # SAFE NORMALIZATION ONLY FOR ENTRY
    # ------------------------------
    if entry_signal is None:
        entry_signal = "NONE"

    # ------------------------------
    # ENTRY FALLBACK ONLY
    # ------------------------------
    if entry_signal == "NONE":
        entry_signal = "BEAR"

    base_entry = map_entry(entry_signal)

    debug_log("[DEBUG] BASE ENTRY:", base_entry)

    # ------------------------------
    # FORCE LAYER (HIGHEST PRIORITY)
    # ------------------------------
    if lhhl_clean in FORCE_UP:
        debug_log("[DEBUG] FORCE → ATMBUY")
        debug_log("===========================================\n")
        return "ATMBUY", raw_entry_signal

    if lhhl_clean in FORCE_DOWN:
        debug_log("[DEBUG] FORCE → ATMSELL")
        debug_log("===========================================\n")
        return "ATMSELL", raw_entry_signal

    debug_log("[DEBUG] NO FORCE → NORMAL MODE")

    # ------------------------------
    # NORMAL MODE
    # ------------------------------
    if lhhl_clean == "UP":
        return ("ATMBUY" if base_entry == "BUY" else base_entry), raw_entry_signal

    if lhhl_clean == "DOWN":
        return ("ATMSELL" if base_entry == "SELL" else base_entry), raw_entry_signal

    # ------------------------------
    # FALLBACK SAFE MODE
    # ------------------------------
    return base_entry, raw_entry_signal


# ==================================================
# RUN
# ==================================================
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
