# sysentrpxy.py
from sysmktpxy import get_signal 
from syscnfgpxy import TICKER 
from sysstrndpxy import get_signal as get_st_signal 
from syskatrpxy import calculate_atr, calculate_dynamic_k 
from datetime import datetime, time 
from zoneinfo import ZoneInfo 

def get_entry_signal(df=None):
    # 1. Fetch Cascade Signals (Confirmed Entry, Trend Exit)
    entry_l4, exit_l2 = get_signal(df) 

    # 2. ST Priority (ATR:ATR Logic)
    st_entry, st_price = get_st_signal(df) 

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # --- MORNING OVERRIDE (Ends exactly at 9:17) ---
    if time(9, 15) <= current_time < time(9, 17):
        if exit_l2 in ["BUY", "BULL", "SELL", "BEAR"]:
            return "MORNING", exit_l2
        return "NONE", exit_l2

    # --- ATR BLOCK ---
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not atr_series.empty else 0

    # --- FINAL ENTRY MAPPING ---
    final_signal = "NONE"

    # IF ST IS BUY/UP
    if st_entry in ["BUY", "UP"]:
        if entry_l4 == "BUY":
            final_signal = "ATMBUY"
        elif entry_l4 == "SELL":
            final_signal = "OTMSELL"
        else:
            final_signal = entry_l4 # BULL/BEAR/NONE

    # IF ST IS SELL/DOWN
    elif st_entry in ["SELL", "DOWN"]:
        if entry_l4 == "SELL":
            final_signal = "ATMSELL"
        elif entry_l4 == "BUY":
            final_signal = "OTMBUY"
        else:
            final_signal = entry_l4 # BULL/BEAR/NONE
            
    # IF ST IS SIDE
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
    entry, ex = get_entry_signal(df)
    print("-" * 36)
    print(f"ENTRY: {entry} | EXIT: {ex}")



