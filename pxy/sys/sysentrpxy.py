# sysentrypxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX
===============================================================================
Operational Rules Matrix:
1. ENTRY Pipeline: Converted cleanly into option targets (ATMBUY / ATMSELL / STANDBY).
                   Requires strict directional alignment between both engines.
2. EXIT Pipeline  : Returns the raw structural engine profile from sysexitpxy.
                    Converts incoming UP/DOWN raw strings into BULL/BEAR cleanly.
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
# Dual-engine streaming pipeline sources
from sysmktpxy import get_signal           # Controls Entry direction
from sysexitpxy import detect_raw_direction # Controls Exit direction (Pure Exit Engine)

def get_entry_signal(df=None):
    """
    Dual-routing pipeline linking live exclusive signals.
    - Converts exit_dir from (UP/DOWN) to (BULL/BEAR) at inception.
    - ENTRY triggers ONLY if sysmktpxy AND translated sysexitpxy match.
    - EXIT returns the converted structural profile cleanly.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    # 1. Fetch live active states from both distinct engine matrices
    mkt_dir, _ = get_signal(df)             # Entry core direction
    _, raw_exit_dir = detect_raw_direction(df)  # Raw Exit Source (Returns UP/DOWN)

    # --- STRING CONVERSION INCEPTION POINT ---
    if raw_exit_dir == "UP":
        exit_dir = "BULL"
    elif raw_exit_dir == "DOWN":
        exit_dir = "BEAR"
    else:
        exit_dir = "NONE"
    # ----------------------------------------

    entry_signal = "STANDBY"
    
    # 2. ROUTE EXIT PIPELINE PURELY (Using the converted structural system)
    exit_signal = exit_dir

    # 3. ENFORCE ALIGNMENT LOGIC FOR ENTRY PIPELINE
    if mkt_dir == "BULL" and exit_dir == "BULL":
        entry_signal = "ATMBUY"
    elif mkt_dir == "BEAR" and exit_dir == "BEAR":
        entry_signal = "ATMSELL"
    else:
        entry_signal = "STANDBY"

    # Console Status Reporting Actions
    if entry_signal != "STANDBY":
        print(f"      🔥 [ACTION] -> ENTRY: {entry_signal} | EXIT: {exit_signal} 🔥")
    else:
        print(f"💤 [STANDBY] -> Alignment Mismatch or Flat Line (MKT: {mkt_dir} | EX: {exit_signal}). Action Terminated. 💤")

    # Returns processed option entry and the explicit structural exit string
    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")

