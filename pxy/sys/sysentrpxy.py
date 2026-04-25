# ==================================================
# sysentrpxy.py (CLEAN: RAW SIGNAL ONLY → ATM MAPPER)
# ==================================================

from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from sysstrndpxy import calculate_supertrend
from datetime import datetime, time
from zoneinfo import ZoneInfo


# ==================================================
# ENTRY ENGINE
# ==================================================
def get_entry_signal(df=None):

    signal, exit_signal = get_signal()

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # ==================================================
    # 🟢 MORNING OVERRIDE ZONE (9:16–9:30)
    # ==================================================
    if time(9, 16) <= current_time < time(9, 30):

        if exit_signal in ["BUY", "BULL"]:
            print("MORNING OVERRIDE → OTMBUY")
            return "OTMBUY", exit_signal

        if exit_signal in ["SELL", "BEAR"]:
            print("MORNING OVERRIDE → OTMSELL")
            return "OTMSELL", exit_signal

        print("MORNING OVERRIDE → NONE")
        return "NONE", exit_signal

    # ==================================================
    # 🔵 AFTER 9:30 → FULL SYSTEM
    # ==================================================

    # BASE SIGNAL
    signal, exit_signal = get_signal()

    # ST FETCH (if needed later in your pipeline)
    data = get_latest_supertrend()
    st = data.get("supertrend", "NEUTRAL").upper()

    is_up = st == "UP"
    is_down = st == "DOWN"

    # ==================================================
    # RAW PASS-THROUGH MODE
    # ==================================================
    if signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 ⛔ 🚧 {signal} 🚧 ⛔".center(36))
        return signal, exit_signal

    # ==================================================
    # NORMAL MAPPING (UNCHANGED LOGIC FLOW)
    # ==================================================
    final_signal = "NONE"

    if signal == "BUY":
        final_signal = "OTMBUY" if is_down else "ATMBUY"

    elif signal == "SELL":
        final_signal = "OTMSELL" if is_up else "ATMSELL"

    elif signal in ["ATMBUY", "ATMSELL"]:
        final_signal = signal

    print(f"{signal} → {final_signal} (ST:{st})".center(36))

    return final_signal, exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
