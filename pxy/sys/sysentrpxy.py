# ==================================================
# sysentrpxy.py (CLEAN: RAW SIGNAL ONLY → ATM MAPPER + ATR REGIME)
# ==================================================

from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from sysstrndpxy import calculate_supertrend
from syskatrpxy import calculate_atr, calculate_dynamic_k
from datetime import datetime, time
from zoneinfo import ZoneInfo


# ==================================================
# ENTRY ENGINE
# ==================================================
def get_entry_signal(df=None):

    signal, exit_signal = get_signal()
    orig_signal = signal

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

    # Supertrend
    df = calculate_supertrend(df)
    last = df.iloc[-1]

    st = str(last["ST_Trend"]).upper()
    is_up = st == "UP"
    is_down = st == "DOWN"

    # ==================================================
    # 📊 ATR BLOCK
    # ==================================================
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not atr_series.empty else 0
    k_value = calculate_dynamic_k(df)

    print(f"ATR:{atr:.2f} | K:{k_value}".center(36))

    # ==================================================
    # RAW PASS-THROUGH MODE
    # ==================================================
    if signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 ⛔ 🚧 {signal} 🚧 ⛔".center(36))
        return signal, exit_signal

    # ==================================================
    # ATR-BASED REGIME LOGIC
    # ==================================================
    final_signal = "NONE"

    if atr > 7:
        # ---- TREND MODE (ORIGINAL LOGIC) ----
        if signal == "BUY":
            final_signal = "BUY" if is_down else "ATMBUY"

        elif signal == "SELL":
            final_signal = "SELL" if is_up else "ATMSELL"

    else:
        # ---- MEAN REVERSION MODE ----
        # SELL above ST, BUY below ST
        if signal == "BUY":
            final_signal = "ATMBUY" if is_down else "BUY"

        elif signal == "SELL":
            final_signal = "ATMSELL" if is_up else "SELL"

    print(f"{signal} → {final_signal} (ST:{st} | ATR:{atr:.2f})".center(36))

    exit_signal = orig_signal
    return final_signal, exit_signal


# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    entry, exit_signal = get_entry_signal()
    print("ENTRY:", entry)
    print("EXIT :", exit_signal)
