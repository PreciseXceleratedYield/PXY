# ==================================================
# sysentrpxy.py (REFACTORED: L4 CASCADE + ST PRIORITY)
# ==================================================
from sysmktpxy import get_signal  # This is the get_signal() we built with L4 Cascade
from syscnfgpxy import TICKER
from sysstrndpxy import calculate_supertrend
from syskatrpxy import calculate_atr, calculate_dynamic_k
from datetime import datetime, time
from zoneinfo import ZoneInfo

# ==================================================
# ENTRY ENGINE
# ==================================================
def get_entry_signal(df=None):
    # 1. Fetch Signals from the L1-L4 Cascade Engine
    # entry_l4: BUY/SELL/BULL/BEAR/NONE
    # exit_l2:  BULL/BEAR/NONE (based on OC/2)
    entry_l4, exit_l2 = get_signal()
    
    # 2. Fetch Absolute Priority from Supertrend 1:1 vs 3:3
    # st_entry: BUY/SELL/UP/DOWN
    st_entry, st_exit = get_st_signal()
    
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # ==================================================
    # 🟢 MORNING OVERRIDE ZONE (9:16–9:30)
    # ==================================================
    if time(9, 16) <= current_time < time(9, 30):
        # Uses OC/2 Flow for morning direction
        if exit_l2 in ["BUY", "BULL"]:
            print("MORNING OVERRIDE → OTMBUY")
            return "OTMBUY", exit_l2
        if exit_l2 in ["SELL", "BEAR"]:
            print("MORNING OVERRIDE → OTMSELL")
            return "OTMSELL", exit_l2
        
        print("MORNING OVERRIDE → NONE")
        return "NONE", exit_l2

    # ==================================================
    # 🔵 AFTER 9:30 → FULL SYSTEM LOGIC
    # ==================================================
    
    # 📊 ATR BLOCK
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not atr_series.empty else 0
    k_value = calculate_dynamic_k(df)
    print(f"ATR:{atr:.2f} | K:{k_value}".center(36))

    # --- FINAL ENTRY MAPPING ---
    final_signal = "NONE"

    # A. ABSOLUTE PRIORITY: ST 1:1 vs 3:3 Cross takes precedence
    if st_entry == "BUY":
        final_signal = "ATMBUY"
    elif st_entry == "SELL":
        final_signal = "ATMSELL"
        
    # B. SECONDARY: L4 Cascade (Gated by ST Direction UP/DOWN)
    elif st_entry == "UP" and entry_l4 == "BUY":
        final_signal = "BUY"
    elif st_entry == "DOWN" and entry_l4 == "SELL":
        final_signal = "SELL"
    
    # C. PASS-THROUGH (STATUS ONLY)
    else:
        final_signal = entry_l4 if entry_l4 in ["BULL", "BEAR"] else "NONE"

    # Formatting and Return
    if final_signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 {final_signal} 🚧 ⛔".center(36))
    else:
        print(f"🔥 {entry_l4} → {final_signal} (ST:{st_entry} | ATR:{atr:.2f})".center(36))

    return final_signal, exit_l2

# ==================================================
# TEST
# ==================================================
if __name__ == "__main__":
    import pandas as pd
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    entry, exit_sig = get_entry_signal(df)
    print("FINAL ENTRY MAPPED:", entry)
    print("FINAL EXIT MAPPED :", exit_sig)

