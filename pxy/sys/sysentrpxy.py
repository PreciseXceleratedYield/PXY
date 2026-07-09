"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX
===============================================================================
Operational Rules Matrix:
1. ENTRY Pipeline: Converted cleanly into option targets (ATMBUY / ATMSELL / NONE).
2. EXIT Pipeline  : Returns the raw structural engine profile (BULL / BEAR / NONE).
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
# Direct streaming source connection from your geometric core engine module
from sysmktpxy import get_signal 

def get_entry_signal(df=None):
    """
    Direct routing pipeline mapping live exclusive raw signals from sysmktpxy.
    - BULL (ACTIVE > PREVIOUS CLOSE) -> ENTRY: ATMBUY  | EXIT: BULL
    - BEAR (ACTIVE < PREVIOUS CLOSE) -> ENTRY: ATMSELL | EXIT: BEAR
    - NONE (ACTIVE == PREVIOUS CLOSE) -> ENTRY: NONE    | EXIT: NONE
    """
    if df is None:
        # FIX: Corrected source module naming conventions to track live ticks safely
        from sysdthapxy import fetch_yf_data
        df = fetch_yf_data()

    # 1. Fetch live active state directly from your geometric module matrix
    # Returns: (execution_state, execution_state)
    direction, _ = get_signal(df)

    entry_signal = "NONE"
    exit_signal = "NONE"

    # 2. MATCH AND ROUTE SHAPES WITH MUTUALLY EXCLUSIVE STRUCTURAL SIGNALS
    if direction == "BULL":
        entry_signal = "ATMBUY"
        exit_signal = "BULL"

    elif direction == "BEAR":
        entry_signal = "ATMSELL"
        exit_signal = "BEAR"
        
    elif direction == "NONE":
        entry_signal = "NONE"
        exit_signal = "NONE"

    # Console Status Reporting Actions
    if entry_signal != "NONE":
        print(f"       🔥 [ACTION] -> {entry_signal} | {exit_signal} 🔥")
    else:
        print("💤 [STANDBY] -> Market Flat Line Detected. Action Terminated. 💤")

    # Returns processed option entry and the explicit structural exit string
    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdthapxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")


