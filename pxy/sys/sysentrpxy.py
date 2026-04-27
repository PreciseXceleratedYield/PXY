# ==================================================
# sysentrpxy.py (STRICT GATING: L4 CASCADE + ST PRIORITY)
# ==================================================
from sysmktpxy import get_signal  # L1-L4 Cascade Engine
from syscnfgpxy import TICKER
from sysstrndpxy import calculate_supertrend as get_st_signal
from syskatrpxy import calculate_atr, calculate_dynamic_k
from datetime import datetime, time
from zoneinfo import ZoneInfo

# ==================================================
# ENTRY ENGINE
# ==================================================
def get_entry_signal(df=None):
    # 1. Fetch L1-L4 Cascade Signals
    # entry_l4: BUY/SELL/BULL/BEAR/NONE
    # exit_l2:  BULL/BEAR/NONE (based on OC/2 Flow)
    entry_l4, exit_l2 = get_signal()
    
    # 2. Fetch Absolute Priority ST 1:1 vs 3:3
    # st_entry: BUY/SELL/UP/DOWN
    st_entry, st_exit = get_st_signal() # ❌ Missing df
   
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # ==================================================
    # 🟢 MORNING OVERRIDE ZONE (9:16–9:30)
    # ==================================================
    if time(9, 16) <= current_time < time(9, 30):
        # Strictly uses OC/2 (exit_l2) for Morning Momentum
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
    
    # 📊 ATR DATA
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not atr_series.empty else 0
    k_value = calculate_dynamic_k(df)
    print(f"ATR:{atr:.2f} | K:{k_value}".center(36))

    # --- FINAL ENTRY MAPPING ENGINE ---
    final_signal = "NONE"

    # A. ABSOLUTE MASTER: ST 1:1 vs 3:3 Crossover takes absolute precedence
    if st_entry == "BUY":
        final_signal = "ATMBUY"
    elif st_entry == "SELL":
        final_signal = "ATMSELL"
        
    # B. SECONDARY: L4 Cascade (Gated by ST UP/DOWN position)
    elif st_entry == "UP" and entry_l4 == "BUY":
        final_signal = "BUY"
    elif st_entry == "DOWN" and entry_l4 == "SELL":
        final_signal = "SELL"
    
    # C. PASS-THROUGH (Status tracking for non-entry candles)
    else:
        # Check if entry_l4 is BULL/BEAR to maintain flow visibility
        if entry_l4 in ["BULL", "BEAR"]:
            final_signal = entry_l4
        else:
            final_signal = "NONE"

    # Console Reporting
    if final_signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 {final_signal} 🚧 ⛔".center(36))
    else:
        print(f"🔥 {entry_l4} → {final_signal} (ST:{st_entry})".center(36))

    # Return the mapped trigger and the OC/2 based exit signal
    return final_signal, exit_l2

# ==================================================
# TEST RUN
# ==================================================
if __name__ == "__main__":
    import pandas as pd
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    entry, exit_sig = get_entry_signal(df)
    print("-" * 36)
    print("FINAL ENTRY MAPPED:", entry)
    print("FINAL EXIT MAPPED :", exit_sig)

