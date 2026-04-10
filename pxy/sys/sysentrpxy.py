# ==================================================
# sysentrpxy.py  (FULL DEBUG MODE)
# ==================================================

from sysmktpxy import get_signal
from syslhhlpxy import get_phase_direction
from datetime import datetime, time
import pytz


TIMEZONE = "Asia/Kolkata"

BLOCK_START = time(9, 14, 0)
BLOCK_END   = time(9, 15, 49)


FORCE_UP = {"ORBUP", "TRASUP", "NONEUP"}
FORCE_DOWN = {"ORBDOWN", "TRANSDOWN", "NONEDOWN"}


# ==================================================
def _map_entry_signal(entry_signal: str) -> str:

    if entry_signal == "BUY":
        return "ATMBUY"
    if entry_signal == "SELL":
        return "ATMSELL"
    return entry_signal


# ==================================================
def get_entry_signal(df=None):

    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz).time()

    print("\n================ DEBUG START ================")

    # ---------------- TIME ----------------
    print("[DEBUG] TIME:", now)

    if BLOCK_START <= now <= BLOCK_END:
        print("[DEBUG] TIME BLOCK ACTIVE → FORCE NONE")
        print("===========================================\n")
        return "NONE", "NONE"

    # ---------------- LHHL ----------------
    _, lhhl = get_phase_direction(df)

    print("[DEBUG] RAW LHHL:", repr(lhhl))

    lhhl_clean = lhhl.strip().upper()

    print("[DEBUG] CLEAN LHHL:", repr(lhhl_clean))

    # ---------------- FORCE CHECK ----------------
    if lhhl_clean in FORCE_UP:
        print("[DEBUG] FORCE MATCH → UP → ATMBUY")
        print("===========================================\n")
        return "ATMBUY", "NONE"

    if lhhl_clean in FORCE_DOWN:
        print("[DEBUG] FORCE MATCH → DOWN → ATMSELL")
        print("===========================================\n")
        return "ATMSELL", "NONE"

    print("[DEBUG] NO FORCE MATCH → entering SIGNAL ENGINE")

    # ---------------- SIGNAL ENGINE ----------------
    entry_signal, exit_signal = get_signal(df)

    print("[DEBUG] ENTRY SIGNAL:", entry_signal)
    print("[DEBUG] EXIT SIGNAL :", exit_signal)

    base_entry = _map_entry_signal(entry_signal)

    print("[DEBUG] BASE ENTRY:", base_entry)

    if lhhl_clean == "UP":
        if base_entry == "BUY":
            print("[DEBUG] UP CONFIRM → ATMBUY")
            print("===========================================\n")
            return "ATMBUY", exit_signal
        print("[DEBUG] UP NO CONFIRM")

    if lhhl_clean == "DOWN":
        if base_entry == "SELL":
            print("[DEBUG] DOWN CONFIRM → ATMSELL")
            print("===========================================\n")
            return "ATMSELL", exit_signal
        print("[DEBUG] DOWN NO CONFIRM")

    print("[DEBUG] FALLBACK RETURN")
    print("===========================================\n")

    return base_entry, exit_signal


# ==================================================
if __name__ == "__main__":

    entry, exit_signal = get_entry_signal()

    print("\nFINAL OUTPUT")
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
