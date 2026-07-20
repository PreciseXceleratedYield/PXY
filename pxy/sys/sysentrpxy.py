"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH SIMPLIFIED CO-ROUTING PIPELINES
===============================================================================
Operational Rules Matrix:
1. Operational window is driven completely and exclusively by sysexitpxy.
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
from sysexitpxy import detect_raw_direction

def get_entry_signal(df=None):
    """
    Dynamically routes option entry and structural exit signals together 
    based strictly on sysexitpxy parameters. Returns raw strings silently.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Dynamic Execution Block using only sysexitpxy
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

    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_entry_signal(df)


