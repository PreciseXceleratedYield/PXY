# sysentrpxy.py
from sysstrndpxy import calculate_supertrend  # <-- Sourced from your upstream module
from sysmktpxy import get_signal  # <-- Import Tier 2 Network Layer (BULL/BEAR Pure Layer)
try:
    from syscnfgpxy import TICKER
except ImportError:
    TICKER = "NSE_INDEX"
import pandas as pd

def get_entry_signal(df=None):
    # Extract Tier 1 Underlying Upstream Trend States (FORCEBUY, FORCESELL, CROSSBUY, CROSSSELL, BULL, BEAR)
    st_trend = "SIDE"
    if df is not None and not df.empty:
        try:
            df_st = calculate_supertrend(df)
            st_trend = str(df_st['ST_Trend'].iloc[-1]).upper()
        except Exception:
            st_trend = "SIDE"

    # --- INDEPENDENT MARKET EXIT LAYER EXTRACTION ---
    mkt_entry, mkt_exit = "NONE", "NONE"
    if df is not None and not df.empty:
        try:
            mkt_entry, mkt_exit = get_signal(df)
            mkt_exit = str(mkt_exit).upper().strip()
        except Exception:
            mkt_exit = "NONE"

    # --- SYNC EXIT LAYER INDEPENDENTLY FROM SYSMKTPXY ---
    if mkt_exit in ["BULL", "BEAR", "NONE"]:
        exit_signal = mkt_exit
    else:
        exit_signal = "NONE"

    # Initialize entry signal to clean baseline neutral state
    final_signal = "NONE"

    # --- DIRECT ROUTER ENGINE (NOW SEGREGATING ATM VS ATM CHANNELS) ---
    # 1. Standard Center Axis Crossover Up -> ATMBUY Execution
    if st_trend == "CROSSBUY":
        final_signal = "ATMBUY"
        
    # 2. Extreme Lower Band Channel Violation -> ATMBUY Execution
    elif st_trend == "FORCEBUY":
        final_signal = "ATMBUY"
        
    # 3. Standard Center Axis Crossover Down -> ATMSELL Execution
    elif st_trend == "CROSSSELL":
        final_signal = "ATMSELL"
        
    # 4. Extreme Upper Band Channel Violation -> ATMSELL Execution
    elif st_trend == "FORCESELL":
        final_signal = "ATMSELL"
        
    # 5. Unfiltered Pure Baseline Trend States Pass-Through
    elif st_trend in ["BULL", "BEAR"]:
        final_signal = st_trend
        
    # Fallback handling for early initialization rows ("SIDE")
    else:
        final_signal = "NONE"

    # --- SEPARATED ACTION VS. INFORMATIONAL LOGGER ---
    is_live_action = final_signal in ["ATMBUY", "ATMSELL", "ATMBUY", "ATMSELL"]
    
    if is_live_action:
        print(f"🔥 En:{final_signal} | Ex:{exit_signal} | St:{st_trend} 🔥")
    elif final_signal in ["BULL", "BEAR"]:
        print(f"ℹ️ En:{final_signal} | Ex:{exit_signal} | St:{st_trend}")
    else:
        print(f"💤 En:{final_signal} | Ex:{exit_signal} | St:{st_trend}")

    return final_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    print("\n=== [TIER 3] Unified STRND Entry + Independent MKT Exit Pipeline Self-Test ===")
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL ENTRY SIGNAL: {entry} | EXIT SIGNAL: {ex}")



