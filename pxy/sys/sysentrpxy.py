"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH SIMPLIFIED CO-ROUTING PIPELINES
===============================================================================
Operational Rules Matrix:
1. Operational window is driven completely and exclusively by SuperTrend.
===============================================================================
"""
import pandas as pd
from syscnfgpxy import TICKER
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Dynamically routes option entry and structural exit signals together 
    based strictly on SuperTrend parameters.
    Returns raw strings silently.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # ===== SUPERTREND PROFILES =====
    processed_st_df = calculate_supertrend(df.copy())
    
    if processed_st_df.empty:
        return "NONE", "NONE"
        
    # Fixed alignment gap: iloc[-1] targets the exact same closed window bar
    trend = processed_st_df['ST_Trend'].iloc[-1]

    # Route Entry and Exit based on pure SuperTrend profile state
    if trend == "BULL":
        entry_signal = "OTMBUY"
        exit_signal = "BULL"
    elif trend == "BEAR":
        entry_signal = "OTMSELL"
        exit_signal = "BEAR"
    else:
        entry_signal = "NONE"
        exit_signal = "NONE"

    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_entry_signal(df)
        print(f"ROUTER SIGNALS >> ENTRY_SIG: {entry} | EXIT_SIG: {ex}")

