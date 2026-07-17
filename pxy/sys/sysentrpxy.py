# pxy_routing_engine.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH INDEPENDENT SEPARATION MATRIX
===============================================================================
Operational Rules Matrix:
1. ENTRY Pipeline: Driven exclusively by sysmktpxy (get_signal) -> ATMBUY/ATMSELL.
2. EXIT Pipeline : Driven exclusively by sysexitpxy (detect_raw_direction) -> BULL/BEAR.
3. No cross-checking or verification checks between systems.
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal 
from sysexitpxy import detect_raw_direction

def get_entry_signal(df=None):
    """
    Direct routing pipeline mapping live exclusive raw signals.
    ENTRY uses sysmktpxy -> maps to ATMBUY/ATMSELL/NONE.
    EXIT uses sysexitpxy -> maps to BULL/BEAR/NONE.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    # 1. Fetch ENTRY direction from the geometric module (sysmktpxy)
    mkt_dir, _ = get_signal(df)

    # 2. Fetch EXIT direction from the direct exit tracker (sysexitpxy)
    _, exit_dir = detect_raw_direction(df)

    # 3. Route ENTRY logic directly (mkt_dir -> entry_signal)
    if mkt_dir == "BULL":
        entry_signal = "ATMBUY"
    elif mkt_dir == "BEAR":
        entry_signal = "ATMSELL"
    else:
        entry_signal = "NONE"

    # 4. Route EXIT logic directly (exit_dir -> exit_signal)
    if exit_dir == "UP":
        exit_signal = "BULL"
    elif exit_dir == "DOWN":
        exit_signal = "BEAR"
    else:
        exit_signal = "NONE"

    # Console Status Reporting Actions
    if entry_signal != "NONE" or exit_signal != "NONE":
        print(f"      🔥 [ACTION] -> ENTRY: {entry_signal} | EXIT: {exit_signal} 🔥")
    else:
        print("💤 [STANDBY] -> Market Flat Line Detected. Action Terminated. 💤")

    # Returns processed option entry and the explicit structural exit string
    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")
