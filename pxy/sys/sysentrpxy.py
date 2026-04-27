# sysentrpxy.py
from sysmktpxy import get_signal  # L1-L4 Cascade Engine
from syscnfgpxy import TICKER
from sysstrndpxy import get_signal as get_st_signal
from syskatrpxy import calculate_atr, calculate_dynamic_k
from datetime import datetime, time
from zoneinfo import ZoneInfo

def get_entry_signal(df=None):
    # 1. Fetch Cascade Signals (L4 Entry, L2 Exit)
    entry_l4, exit_l2 = get_signal()
    
    # 2. ST Priority & Directional Flow (Body Crossover Logic)
    # st_entry returns: BUY, SELL, UP, or DOWN
    st_entry, st_exit = get_st_signal(df)
    
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    current_time = now.time()

    # --- MORNING OVERRIDE (9:16–9:30) ---
    if time(9, 16) <= current_time < time(9, 30):
        if exit_l2 in ["BUY", "BULL"]: return "OTMBUY", exit_l2
        if exit_l2 in ["SELL", "BEAR"]: return "OTMSELL", exit_l2
        return "NONE", exit_l2

    # --- ATR BLOCK ---
    atr_series = calculate_atr(df)
    atr = atr_series.iloc[-1] if not atr_series.empty else 0
    print(f"ATR:{atr:.2f}".center(36))

    # --- FINAL ENTRY MAPPING (STRICT TRIPLE ALIGNMENT) ---
    final_signal = "NONE"

    # A. ST CROSSOVER (Absolute Priority Reversal)
    if st_entry == "BUY":
        final_signal = "STBUY"
    elif st_entry == "SELL":
        final_signal = "STSELL"
        
    # B. BULLISH ZONE (ST is UP - Body Above Line)
    elif st_entry == "UP":
        if entry_l4 == "BUY": 
            final_signal = "BUY"
        elif entry_l4 == "BULL": 
            final_signal = "BULL"

    # C. BEARISH ZONE (ST is DOWN - Body Below Line)
    elif st_entry == "DOWN":
        if entry_l4 == "SELL": 
            final_signal = "SELL"
        elif entry_l4 == "BEAR": 
            final_signal = "BEAR"

    # D. Final Strict Logic Check (Log Formatting)
    if final_signal in ["BULL", "BEAR", "NONE"]:
        print(f"⛔ 🚧 NO ENTRY 🚧 {final_signal} 🚧 ⛔".center(36))
    else:
        print(f"🔥 {entry_l4} → {final_signal} (ST_ZONE:{st_entry})".center(36))

    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    entry, ex = get_entry_signal(df)
    print("-" * 36)
    print(f"ENTRY: {entry} | EXIT: {ex}")


