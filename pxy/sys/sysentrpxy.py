# sysentrpxy.py
from sysmktpxy import get_signal  # L1-L4 Cascade Engine
from syscnfgpxy import TICKER
from sysstrndpxy import calculate_supertrend
from syskatrpxy import calculate_atr, calculate_dynamic_k
from datetime import datetime, time
from zoneinfo import ZoneInfo

def get_entry_signal(df=None):
    # 1. Fetch Cascade Signals (L4 Entry, L2 Exit)
    entry_l4, exit_l2 = get_signal()
    
    # 2. Absolute Priority: ST 1:1 vs 3:3 Crossover
    # We call your function twice with the required hardcoded values
    df_fast = calculate_supertrend(df, period=1, multiplier=1)
    df_slow = calculate_supertrend(df, period=3, multiplier=3)
    
    f_curr, f_prev = df_fast['ST'].iloc[-1], df_fast['ST'].iloc[-2]
    s_curr, s_prev = df_slow['ST'].iloc[-1], df_slow['ST'].iloc[-2]
    
    # Logic for st_entry (BUY/SELL/UP/DOWN)
    if f_prev <= s_prev and f_curr > s_curr:
        st_entry = "BUY"
    elif f_prev >= s_prev and f_curr < s_curr:
        st_entry = "SELL"
    elif f_curr > s_curr:
        st_entry = "UP"
    else:
        st_entry = "DOWN"

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # ==================================================
    # 🟢 MORNING OVERRIDE ZONE (9:16–9:30)
    # ==================================================
    if time(9, 16) <= current_time < time(9, 30):
        if exit_l2 in ["BUY", "BULL"]:
            print("MORNING OVERRIDE → OTMBUY")
            return "OTMBUY", exit_l2
        if exit_l2 in ["SELL", "BEAR"]:
            print("MORNING OVERRIDE → OTMSELL")
            return "OTMSELL", exit_l2
        return "NONE", exit_l2

    # ==================================================
    # 🔵 AFTER 9:30 → FULL SYSTEM LOGIC
    # ==================================================
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not atr_series.empty else 0
    k_value = calculate_dynamic_k(df)
    print(f"ATR:{atr:.2f} | K:{k_value}".center(36))

    # --- FINAL ENTRY MAPPING ---
    final_signal = "NONE"

    # Priority A: Absolute ST Crossover
    if st_entry == "BUY":
        final_signal = "ATMBUY"
    elif st_entry == "SELL":
        final_signal = "ATMSELL"
        
    # Priority B: L4 Cascade (Gated by ST Direction)
    elif st_entry == "UP" and entry_l4 == "BUY":
        final_signal = "BUY"
    elif st_entry == "DOWN" and entry_l4 == "SELL":
        final_signal = "SELL"
    
    # Priority C: Status Pass-through
    else:
        final_signal = entry_l4 if entry_l4 in ["BULL", "BEAR"] else "NONE"

    if final_signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 {final_signal} 🚧 ⛔".center(36))
    else:
        print(f"🔥 {entry_l4} → {final_signal} (ST:{st_entry})".center(36))

    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    entry, ex = get_entry_signal(df)
    print(f"ENTRY: {entry} | EXIT: {ex}")


