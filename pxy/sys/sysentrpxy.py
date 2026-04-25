# ==================================================
# sysentrpxy.py (CLEAN: RAW SIGNAL ONLY → ATM MAPPER)
# ==================================================

from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from systdaypxy import get_market_snapshot  # adjust if needed
from sysstrndpxy import get_latest_supertrend
from datetime import datetime, time
from zoneinfo import ZoneInfo


# ==================================================
# ENTRY ENGINE (NO INDICATORS)
# ==================================================
def get_entry_signal(df=None):

    # ------------------------------
    # BASE SIGNAL
    # ------------------------------
    signal, exit_signal = get_signal()

    # ------------------------------
    # ST FETCH (REPLACES BIAS)
    # ------------------------------
    data = get_latest_supertrend()

    st = data.get("supertrend", "NEUTRAL").upper()

    is_up = st == "UP"
    is_down = st == "DOWN"

    # ------------------------------
    # TIME BLOCK (IST)
    # ------------------------------
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    if time(9, 14) <= current_time < time(9, 16):
        print("[⏱️ ⌛] 09:14–09:16 → NO TRADE")
        return "NONE", exit_signal

    if time(9, 16) <= current_time < time(9, 20):
        print("[⏱️ ⌛] 09:16–09:20 → DIRECT ATM (NO FILTER)")

        if exit_signal in ["BUY", "BULL"]:
            return "ATMBUY", exit_signal

        if exit_signal in ["SELL", "BEAR"]:
            return "ATMSELL", exit_signal

        return "NONE", exit_signal

    # ==================================================
    # RAW PASS-THROUGH MODE
    # ==================================================
    if signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 ⛔ 🚧 {signal} 🚧 ⛔".center(36))
        return signal, exit_signal

    # ==================================================
    # ST MAPPING ONLY (REPLACES BIAS LOGIC)
    # ==================================================
    final_signal = "NONE"

    if signal == "BUY":
        final_signal = "OTMBUY" if is_down else "ATMBUY"

    elif signal == "SELL":
        final_signal = "OTMSELL" if is_up else "ATMSELL"

    elif signal in ["ATMBUY", "ATMSELL"]:
        final_signal = signal

    # ------------------------------
    # OUTPUT
    # ------------------------------
    print(f"{signal} → {final_signal} (ST:{st})".center(36))

    return final_signal, exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
