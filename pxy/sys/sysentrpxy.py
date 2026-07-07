"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX
===============================================================================
Operational Rules Matrix:
1. ENTRY Pipeline: Converted cleanly into option targets (KTMBUY / KTMSELL).
2. EXIT Pipeline  : Returns the raw structural engine profile (BULL / BEAR).
===============================================================================
"""

from sysexitpxy import detect_raw_direction
from syscnfgpxy import TICKER
import pandas as pd

def get_entry_signal(df=None):
    """
    Direct routing pipeline mapping live raw directions.
    - UP (ACTIVE > CLOSED)   -> ENTRY: KTMBUY  | EXIT: BULL
    - DOWN (ACTIVE < CLOSED) -> ENTRY: KTMSELL | EXIT: BEAR
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    # 1. Fetch raw direction state directly from your sysexitpxy file engine
    _, direction = detect_raw_direction(df)

    entry_signal = "NONE"
    exit_signal = "NONE"

    # 2. MATCH AND ROUTE SHAPES UNCONDITIONALLY
    if direction == "UP":
        entry_signal = "KTMBUY"
        exit_signal = "BULL"

    elif direction == "DOWN":
        entry_signal = "KTMSELL"
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
