# sysentrpxy.py
from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from sysstrndpxy import get_signal as get_st_signal
from syskatrpxy import calculate_atr, calculate_dynamic_k
from syshkinpxy import detect_ha_flip_signal
from datetime import datetime, time
from zoneinfo import ZoneInfo

def get_entry_signal(df=None):
    # 1. Fetch Cascade Signals (Confirmed Entry, Trend Exit)
    entry_l4, exit_l2 = get_signal(df)

    # 2. ST Priority (SuperTrend Logic)
    st_entry, st_price = get_st_signal(df)

    # Time Management
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # --- MORNING OVERRIDE (9:15 to 10:00) ---
    if time(9, 15) <= current_time < time(10, 00):
        if exit_l2 == "BUY":
            return "OTMBUY", exit_l2
        elif exit_l2 == "SELL":
            return "OTMSELL", exit_l2
        elif exit_l2 in ["BULL", "BEAR"]:
            return exit_l2, exit_l2
        return "NONE", exit_l2

    # --- ATR BLOCK (Only reached AFTER 10:00) ---
    # Defining the values requested
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not (atr_series is None or atr_series.empty) else 0
    k_val = calculate_dynamic_k(df)
    ha_sig, past_d, ce_d, pe_d = detect_ha_flip_signal(df)

    # --- FINAL ENTRY MAPPING ---
    final_signal = "NONE"

    # IF ST IS BUY/UP
    if st_entry in ["BUY", "UP"]:
        if entry_l4 == "BUY":
            final_signal = "ATMBUY"
        elif entry_l4 == "SELL":
            final_signal = "OTMSELL"
        else:
            final_signal = entry_l4

    # IF ST IS SELL/DOWN
    elif st_entry in ["SELL", "DOWN"]:
        if entry_l4 == "SELL":
            final_signal = "ATMSELL"
        elif entry_l4 == "BUY":
            final_signal = "OTMBUY"
        else:
            final_signal = entry_l4

    # IF ST IS SIDEWAY
    else:
        final_signal = entry_l4

    # Reporting
    if final_signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 {final_signal} 🚧 ⛔".center(36))
    else:
        print(f"🔥 {entry_l4} → {final_signal} (ST:{st_entry})".center(36))

    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 36)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")
