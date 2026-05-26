# sysentrpxy.py
from sysstrndpxy import calculate_supertrend  # <-- Import Tier 1 42 TSMA Engine
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

    # Initialize output signals to clean baseline neutral states
    final_signal = "NONE"
    exit_signal = "NONE"

    # --- CORE TREND PRIORITY ROUTER (DEPENDS ON STRND ONLY) ---
    
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

    # --- SYNC EXIT LAYER WITH REFINED STRUCTURAL EXPECTATIONS ---
    # Strictly maps your structural trend states to BULL, BEAR, SELL, BUY, or NONE
    if st_trend in ["CROSSBUY", "FORCEBUY", "TRENDBUY"]:
        exit_signal = "BUY"
    elif st_trend in ["CROSSSELL", "FORCESELL", "TRENDSELL"]:
        exit_signal = "SELL"
    elif st_trend in ["BULL", "BEAR"]:
        exit_signal = st_trend
    else:
        exit_signal = "NONE"

    # --- SEPARATED ACTION VS. INFORMATIONAL LOGGER ---
    is_live_action = final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]
    
    if is_live_action:
        print(f"🔥 ACTION : {final_signal} | EXIT MAP: {exit_signal} | TREND STATE: {st_trend} 🔥")
    elif final_signal in ["BULL", "BEAR"]:
        print(f"ℹ️ INFO ONLY : {final_signal} | EXIT MAP: {exit_signal} | TREND STATE: {st_trend}")
    else:
        print(f"💤 NEUTRAL STATE : {final_signal} | EXIT MAP: {exit_signal} | TREND STATE: {st_trend}")

    return final_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    print("\n=== [TIER 3] Unified STRND Pass-Through Pipeline Self-Test ===")
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL ENTRY SIGNAL: {entry} | EXIT SIGNAL: {ex}")

