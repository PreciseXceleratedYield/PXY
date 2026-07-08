"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX
===============================================================================
Operational Rules Matrix:
1. ENTRY Pipeline: Converted cleanly into option targets (ATMBUY / ATMSELL).
2. EXIT Pipeline  : Returns the raw structural engine profile (BULL / BEAR).
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
# Feed directly from the newly integrated geometric pxy_engine
from sysmktpxy import get_signal 

def get_entry_signal(df=None):
    """
    Direct routing pipeline mapping live raw directions from pxy_engine.
    - BULL (ACTIVE > CLOSED) -> ENTRY: ATMBUY  | EXIT: BULL
    - BEAR (ACTIVE < CLOSED) -> ENTRY: ATMSELL | EXIT: BEAR
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    # 1. Fetch live active state directly from your geometric engine module
    # get_signal returns (execution_state, execution_state) i.e. ("BULL"/"BEAR", "BULL"/"BEAR")
    direction, _ = get_signal(df)

    entry_signal = "NONE"
    exit_signal = "NONE"

    # 2. MATCH AND ROUTE SHAPES UNCONDITIONALLY FROM PXY_ENGINE
    if direction == "BULL":
        entry_signal = "ATMBUY"
        exit_signal = "BULL"

    elif direction == "BEAR":
        entry_signal = "ATMSELL"
        exit_signal = "BEAR"

    # Console Status Reporting Actions
    if entry_signal != "NONE":
        print(f"🔥 [ACTION] -> {entry_signal} | {exit_signal} 🔥")

    # Returns processed option entry and the explicit structural exit string
    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")

