# sysentrypxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX
===============================================================================
Operational Rules Matrix:
1. ENTRY Pipeline: Converted cleanly into option targets (ATMBUY / ATMSELL / WAIT).
                   Requires strict directional alignment between both engines.
2. EXIT Pipeline  : Derived unfiltered and directly from the sysmktpxy engine.
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
# Dual-engine streaming pipeline sources
from sysmktpxy import get_signal           # Primary Entry & Direct Pure Exit Engine
from sysexitpxy import detect_raw_direction # Used strictly for Entry Alignment validation

def get_entry_signal(df=None):
    """
    Dual-routing pipeline linking live exclusive signals.
    - ENTRY triggers ONLY if sysmktpxy AND translated sysexitpxy match (Aligned).
    - EXIT bypasses filtering entirely and tracks sysmktpxy directly.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    # 1. Fetch live active states from both distinct engine matrices
    mkt_dir, _ = get_signal(df)                 # Direct Source for Exit & Entry target
    _, raw_exit_dir = detect_raw_direction(df)  # Used only to validate entry alignment

    # --- STRING CONVERSION FOR ENTRY ALIGNMENT CHECK ---
    if raw_exit_dir == "UP":
        exit_dir = "BULL"
    elif raw_exit_dir == "DOWN":
        exit_dir = "BEAR"
    else:
        exit_dir = "NONE"
    # ---------------------------------------------------

    entry_signal = "WAIT"
    
    # 2. ROUTE EXIT PIPELINE PURELY & UNFILTERED (Directly from sysmktpxy)
    exit_signal = mkt_dir if mkt_dir in ["BULL", "BEAR"] else "NONE"

    # 3. ENFORCE ALIGNMENT LOGIC FOR ENTRY PIPELINE
    if mkt_dir == "BULL" and exit_dir == "BULL":
        entry_signal = "ATMBUY"
    elif mkt_dir == "BEAR" and exit_dir == "BEAR":
        entry_signal = "ATMSELL"
    else:
        entry_signal = "WAIT"

    # Console Status Reporting Actions
    if entry_signal != "WAIT":
        print(f"   🔥 [ACTION] -> ENTRY: {entry_signal} | EXIT: {exit_signal} 🔥")
    else:
        print(f"[WAIT]-Mismatch (MKT:{mkt_dir} | ST:{exit_dir})")

    # Returns processed option entry and the explicit structural exit string
    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")

