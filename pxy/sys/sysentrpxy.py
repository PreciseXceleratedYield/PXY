# ==================================================
# sysentrpxy.py (CLEAN: RAW SIGNAL ONLY → ATM MAPPER)
# ==================================================

from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from your_snapshot_file import get_market_snapshot  # adjust if needed
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
    # BIAS FETCH
    # ------------------------------
    data = get_market_snapshot(TICKER)
    bias = data["bias"] if data else "NEUTRAL"

    # simple normalization
    bias_u = bias.upper()
    is_bear = "BEAR" in bias_u
    is_bull = "BULL" in bias_u

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
    # BIAS MAPPING ONLY (CORE LOGIC)
    # ==================================================
    final_signal = "NONE"

    if signal == "BUY":
        final_signal = "OTMBUY" if is_bear else "ATMBUY"

    elif signal == "SELL":
        final_signal = "OTMSELL" if is_bull else "ATMSELL"

    elif signal in ["ATMBUY", "ATMSELL"]:
        final_signal = signal

    # ------------------------------
    # OUTPUT
    # ------------------------------
    print(f"{signal} → {final_signal} ({bias})".center(36))

    return final_signal, exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
