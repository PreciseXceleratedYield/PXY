# sysentrpxy.py
from sysmktpxy import get_signal  # <-- Import from Tier 2 Network Layer
from sysstrndpxy import calculate_supertrend  # <-- Import Tier 1 42 SMA Engine
try:
    from syscnfgpxy import TICKER
except ImportError:
    TICKER = "NSE_INDEX"
import pandas as pd

def get_entry_signal(df=None):
    # 1. Fetch Raw Signals from Tier 2 Network Layer (BUY, SELL, BULL, BEAR, or NONE)
    entry_signal, exit_signal = get_signal(df)
    if entry_signal:
        entry_signal = entry_signal.upper()

    # 2. Extract Tier 1 Underlying 42 SMA Trend States (BUY, SELL, BULL, BEAR)
    st_trend = "SIDE"
    if df is not None and not df.empty:
        try:
            df_st = calculate_supertrend(df)
            st_trend = str(df_st['ST_Trend'].iloc[-1]).upper()
        except Exception:
            st_trend = "SIDE"

    # Initialize final signal to a clean neutral state
    final_signal = "NONE"

    # 3. CORE TREND PRIORITY ROUTER (ENTRY ONLY)
    
    # Priority 1: Fresh 42 SMA Crossover signals take absolute priority over everything
    if st_trend == "AVGB":
        final_signal = "STBUY"
    elif st_trend == "AVGS":
        final_signal = "STSELL"
        
    # Priority 2: Direct Ongoing State Pass-Through (If market layer sends BULL or BEAR)
    elif entry_signal in ["BULL", "BEAR"]:
        final_signal = entry_signal
        
    # Priority 3: Ongoing Trend State Filters (Strict Explicit Inverse Rules)
    elif st_trend == "BULL":
        if entry_signal == "SELL":
            final_signal = "OTMSELL"  # FIXED: Counter-trend short changed from NONE to OTMSELL
        else:
            final_signal = entry_signal  # Every other signal passes as is (BUY -> BUY, NONE -> NONE)
            
    elif st_trend == "BEAR":
        if entry_signal == "BUY":
            final_signal = "OTMBUY"   # FIXED: Counter-trend long changed from NONE to OTMBUY
        else:
            final_signal = entry_signal  # Every other signal passes as is (SELL -> SELL, NONE -> NONE)
            
    else:
        # Fallback safety block for early data rows ("SIDE")
        final_signal = "NONE"

    # 4. FORCE ALL CONFIRMED ENTRY ACTION CHANNELS TO STRIKE SIGNALS
    # Kept ATM completely as is. Standardized filtered triggers.
    if final_signal == "BUY":
        final_signal = "ATMBUY"
    elif final_signal == "SELL":
        final_signal = "ATMSELL"

    # 5. ABSOLUTE END CATCH-ALL: Informational Fallback
    is_live_action = final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]
    
    if final_signal == "NONE":
        final_signal = exit_signal

    # 6. SEPARATED ACTION VS. INFORMATIONAL LOGGER
    if is_live_action:
        print(f"🔥 ACTION : {final_signal} | TREND STATE: {st_trend} 🔥")
    elif final_signal in ["BUY", "SELL", "BULL", "BEAR"]:
        print(f"ℹ️ INFO ONLY : {final_signal} | TREND STATE: {st_trend}")

    return final_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    print("\n=== [TIER 3] Complete State Pass-Through Pipeline Self-Test ===")
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL ENTRY SIGNAL: {entry} | EXIT SIGNAL: {ex}")
