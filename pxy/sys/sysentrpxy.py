# ==================================================
# sysentrpxy.py (CLEAN PRODUCTION VERSION)
# ==================================================

from sysmktpxy import get_signal
from syslhhlpxy import get_phase_direction
from sysdtafpxy import fetch_yf_data
from datetime import datetime, time
import pytz

DEBUG = False

def debug_log(*args):
    if DEBUG:
        print(*args)


TIMEZONE = "Asia/Kolkata"

BLOCK_NONE_START = time(9, 14)
BLOCK_NONE_END   = time(9, 15, 59)

FORCE_UP = {"ORBUP", "TRASUP", "NONEUP"}
FORCE_DOWN = {"ORBDOWN", "TRANSDOWN", "NONEDOWN"}


def map_entry(sig):
    if sig == "BUY":
        return "ATMBUY"
    if sig == "SELL":
        return "ATMSELL"
    return sig


def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    debug_log("\n================ DEBUG START ================")
    debug_log("[DEBUG] TIME:", now)

    if BLOCK_NONE_START <= now <= BLOCK_NONE_END:
        return "NONE", "NONE"

    if df is None:
        df = fetch_yf_data(period="5d", interval="1m")

    if df is None or len(df) < 3:
        return "NONE", "NONE"

    df = df.copy()

    debug_log("[DEBUG] DF READY:", df.shape)

    phase, lhhl = get_phase_direction(df)

    lhhl_clean = str(lhhl).strip().upper()
    debug_log("[DEBUG] LHHL:", lhhl_clean)

    # ------------------------------
    # PURE SIGNALS (NO MODIFICATION)
    # ------------------------------
    entry_signal, exit_signal = get_signal()

    debug_log("[DEBUG] ENTRY SIGNAL:", entry_signal)
    debug_log("[DEBUG] EXIT SIGNAL :", exit_signal)

    # ------------------------------
    # ENTRY PROCESS ONLY
    # ------------------------------
    if entry_signal is None:
        entry_signal = "NONE"

    if entry_signal == "NONE":
        entry_signal = "BEAR"

    base_entry = map_entry(entry_signal)

    debug_log("[DEBUG] BASE ENTRY:", base_entry)

    # ------------------------------
    # FORCE LAYER (ENTRY ONLY)
    # ------------------------------
    if lhhl_clean in FORCE_UP:
        return "ATMBUY", exit_signal

    if lhhl_clean in FORCE_DOWN:
        return "ATMSELL", exit_signal

    # ------------------------------
    # NORMAL MODE
    # ------------------------------
    if lhhl_clean == "UP":
        return ("ATMBUY" if base_entry == "BUY" else base_entry), exit_signal

    if lhhl_clean == "DOWN":
        return ("ATMSELL" if base_entry == "SELL" else base_entry), exit_signal

    return base_entry, exit_signal


if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
