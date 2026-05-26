# sysentrpxy.py
from sysstrndpxy import calculate_supertrend  # <-- Import Tier 1 42 TSMA Engine
from sysmktpxy import get_signal  # <-- Import Tier 2 Network Layer (BULL/BEAR Pure Layer)
try:
    from syscnfgpxy import TICKER
except ImportError:
    TICKER = "NSE_INDEX"
import pandas as pd

def get_entry_signal(df=None):
    # Extract Tier 1 Underlying 42 TSMA Trend States
    st_trend = "SIDE"
    if df is not None and not df.empty:
        try:
            df_st = calculate_supertrend(df)
            st_trend = str(df_st['ST_Trend'].iloc[-1]).upper()
        except Exception:
            st_trend = "SIDE"

    # --- INDEPENDENT MARKET EXIT LAYER EXTRACTION ---
    # Fetch background context directly from sysmktpxy module independently
    mkt_entry, mkt_exit = "NONE", "NONE"
    if df is not None and not df.empty:
        try:
            mkt_entry, mkt_exit = get_signal(df)
            mkt_exit = str(mkt_exit).upper().strip()
        except Exception:
            mkt_exit = "NONE"

    # Initialize entry signal to clean baseline neutral state
    final_signal = "NONE"

    # --- CORE TREND PRIORITY ROUTER (ENTRY DEPENDS ON STRND ONLY) ---
    
    # 1. ATMBUY Channel Configurations (Crossovers & Trajectory Channel Swings)
    if st_trend in ["CROSSBUY", "TRENDBUY"]:
        final_signal = "ATMBUY"
        
    # 2. OTMBUY Channel Configurations (Extreme Force Boundary Breakouts)
    elif st_trend == "FORCEBUY":
        final_signal = "OTMBUY"
        
    # 3. ATMSELL Channel Configurations (Crossovers & Trajectory Channel Swings)
    elif st_trend in ["CROSSSELL", "TRENDSELL"]:
        final_signal = "ATMSELL"
        
    # 4. OTMSELL Channel Configurations (Extreme Force Boundary Breakouts)
    elif st_trend == "FORCESELL":
        final_signal = "OTMSELL"
        
    # 5. Unfiltered Trend States Pass-Through
    elif st_trend in ["BULL", "BEAR"]:
        final_signal = st_trend
        
    # Fallback handling for early initialization rows ("SIDE")
    else:
        final_signal = "NONE"

    # --- SYNC EXIT LAYER INDEPENDENTLY FROM SYSMKTPXY ---
    # Overridden completely to rely strictly on the flattened market signals: BULL, BEAR, or NONE
    if mkt_exit in ["BULL", "BEAR", "NONE"]:
        exit_signal = mkt_exit
    else:
        exit_signal = "NONE"

    # --- SEPARATED ACTION VS. INFORMATIONAL LOGGER ---
    is_live_action = final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]
    
    if is_live_action:
        print(f"🔥 ACTION : {final_signal} | EXIT: {exit_signal} | TREND: {st_trend} 🔥")
    elif final_signal in ["BULL", "BEAR"]:
        print(f"ℹ️ INFO : {final_signal} | EXIT: {exit_signal} | TREND: {st_trend}")
    else:
        print(f"💤 NEUTRAL : {final_signal} | EXIT: {exit_signal} | TREND: {st_trend}")

    return final_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    print("\n=== [TIER 3] Unified STRND Entry + Independent MKT Exit Pipeline Self-Test ===")
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL ENTRY SIGNAL: {entry} | EXIT SIGNAL: {ex}")


