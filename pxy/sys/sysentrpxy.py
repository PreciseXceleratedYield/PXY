"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH SIMPLIFIED CO-ROUTING PIPELINES
===============================================================================
Operational Rules Matrix:
1. Operational window is driven completely and exclusively by sysmktpxy.
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal  # ✅ Solo retrieval derived directly from sysmktpxy
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    """
    Dynamically routes option entry and structural exit signals together 
    based strictly on sysmktpxy parameters. Returns raw strings silently.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Dynamic Execution Block pulling exclusively from your running momentum engine
    entry_dir, exit_dir = get_signal(df)
    
    # ===== SUPERTREND PROFILES =====
    processed_st_df = calculate_supertrend(df.copy())
    # Fixed alignment gap: iloc[-1] targets the exact same closed window bar 
    trend = processed_st_df['ST_Trend'].iloc[-1] if not processed_st_df.empty else "NONE"
    
    # Route Entry and Exit based on raw direction (BULL / BEAR) from sysmktpxy
    if entry_dir == "BULL":
        # While TREND IS BEAR we do OTMBUY, flip to ATMBUY otherwise
        entry_signal = "OTMBUY" if trend == "BEAR" else "ATMBUY"
        exit_signal = "BULL"
    elif entry_dir == "BEAR":
        # While TREND IS BULL we do OTMSELL, flip to ATMSELL otherwise
        entry_signal = "OTMSELL" if trend == "BULL" else "ATMSELL"
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

