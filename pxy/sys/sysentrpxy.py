"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX
===============================================================================
Operational Rules Matrix:
1. BULL / BUY States: Maps directly to entry options (OTMBUY) without filter.
2. BEAR / SELL States: Maps directly to entry options (OTMSELL) without filter.
===============================================================================
"""

from sysmktpxy import get_signal as get_market_shape
from syscnfgpxy import TICKER
from datetime import datetime
import pandas as pd

def get_entry_signal(df=None):
    """
    Direct routing pipeline mapping live market states straight to OTM entries.
    - BULL / BUY  -> Converted directly to OTMBUY
    - BEAR / SELL -> Converted directly to OTMSELL
    """
    # 1. Fetch raw geometric live market state from your engine
    mkt_entry, exit_l2 = get_market_shape(df)

    final_signal = "NONE"

    # 2. PURE ENTRY OTM ROUTING MATRIX
    if mkt_entry in ["BULL", "BUY"]:
        # Direct conversion to Out-The-Money Call options entry
        final_signal = "OTMBUY"

    elif mkt_entry in ["BEAR", "SELL"]:
        # Direct conversion to Out-The-Money Put options entry
        final_signal = "OTMSELL"

    else:
        # Default safety fallback state for flat market profiles (NONE)
        final_signal = "NONE"

    # Console Status Reporting Actions
    if final_signal != "NONE":
        print(f"🔥 [ROUTING ENGINE ENTRY ACTION] -> {final_signal} 🔥")

    # Returns the processed entry signal and completely untouched raw exit_l2 pipeline
    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")


