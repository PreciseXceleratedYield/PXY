"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH SIMPLIFIED CO-ROUTING PIPELINES
===============================================================================
Operational Rules Matrix:
1. Operational window is driven completely and exclusively by sysexitpxy.
===============================================================================
"""

import pandas as pd  # Added import back here
from syscnfgpxy import TICKER
from sysexitpxy import detect_raw_direction

def get_entry_signal(df=None):
    """
    Dynamically routes option entry and structural exit signals together 
    based strictly on sysexitpxy parameters.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Extract the exact IST time components from the latest candle timestamp
    latest_timestamp = df.index[-1]

    # 2. Dynamic Execution Block using only sysexitpxy
    _, exit_dir = detect_raw_direction(df)
    
    # Route Entry and Exit based on raw direction
    if exit_dir == "UP":
        entry_signal = "ATMBUY"
        exit_signal = "BULL"
    elif exit_dir == "DOWN":
        entry_signal = "ATMSELL"
        exit_signal = "BEAR"
    else:
        entry_signal = "NONE"
        exit_signal = "NONE"
        
    routing_mode_text = "[MODE: PURE EXITPXY DRIVEN]"

    # 3. Console Status Reporting Actions
    print(f"🕒 Time: {latest_timestamp.strftime('%H:%M')} IST | {routing_mode_text}")
    if entry_signal != "NONE" or exit_signal != "NONE":
        print(f"      🔥 [ACTION] -> ENTRY: {entry_signal} | EXIT: {exit_signal} 🔥")
    else:
        print("💤 [STANDBY] -> Market Flat Line Detected. Action Terminated. 💤")

    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")

