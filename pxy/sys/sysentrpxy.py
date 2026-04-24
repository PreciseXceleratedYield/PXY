# ==================================================
# sysentrpxy.py (CLEAN: RAW SIGNAL ONLY → ATM MAPPER)
# ==================================================

from sysmktpxy import get_signal
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
    orig_signal = signal

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
    # RAW PASS-THROUGH MODE (NO FILTERS)
    # ==================================================
    if signal in ["BULL", "BEAR", "NONE"]:
        line = f"⛔ 🚧 NO ENTRY 🚧 ⛔ 🚧 {signal} 🚧 ⛔"
        print(line.center(36))
        return signal, exit_signal

    # ==================================================
    # SIMPLE ATM MAPPING (CORE LOGIC ONLY)
    # ==================================================
    final_signal = "NONE"

    if signal in ["BUY"]:
        final_signal = "ATMBUY"

    elif signal in ["SELL"]:
        final_signal = "ATMSELL"

    elif signal in ["ATMBUY", "ATMSELL"]:
        final_signal = signal

    # ------------------------------
    # FINAL PRINT
    # ------------------------------
    print(f"{signal} → {final_signal}".center(36))
    final_signal = "ATMSELL"

    return final_signal, exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
