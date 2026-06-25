"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX
===============================================================================
Operational Rules Matrix:
1. BULL / BEAR Candlesticks: Passes downstream unconditionally as pure exit signal.
2. BUY / SELL Cross: Maps directly to entry options (OTMBUY / OTMSELL) without filter.
===============================================================================
"""

from sysmktpxy import get_signal as get_market_shape
from syscnfgpxy import TICKER
from datetime import datetime
import pandas as pd

def get_entry_signal(df=None):
    """
    Direct routing pipeline mapping closed vs running market states.
    - BULL / BEAR -> Passed through exactly (Pure Exit Signal Profile)
    - BUY / SELL   -> Converted directly to OTMBUY / OTMSELL (Pure Entry Profile)
    """
    # 1. Fetch raw geometric market state from your engine
    mkt_entry, exit_l2 = get_market_shape(df)

    final_signal = "NONE"

    # 2. STRIPPED FILTER MATRIX ROUTING PIPELINE
    if mkt_entry in ["BULL", "BEAR"]:
        # Unconditional pass-through for straight continuation states
        final_signal = mkt_entry

    elif mkt_entry == "BUY":
        # Straight crossover conversion to OTM asset targets
        final_signal = "OTMBUY"

    elif mkt_entry == "SELL":
        # Straight crossover conversion to OTM asset targets
        final_signal = "OTMSELL"

    else:
        # Default safety fallback state
        final_signal = "NONE"

    # Console Status Reporting Actions
    if final_signal != "NONE":
        print(f"🔥 [ROUTING ENGINE ACTION] -> {final_signal} 🔥")

    # Returns the direct final_signal and completely untouched raw exit_l2 pipeline
    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")

