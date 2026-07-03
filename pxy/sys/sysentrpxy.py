"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX & REGIME PRIORITY
===============================================================================
Operational Rules Matrix:
1. EXIT Pipeline  : Unconditionally mapped to get_signal (UP -> BULL | DOWN -> BEAR).
2. ENTRY Pipeline : Filtered by SuperTrend crossover and continuation regimes.
                    SIDE state bypasses filters and follows live direction.
===============================================================================
"""

# Import the signal functions from your engines
from sysmktpxy import get_signal      # Direction engine (UP / DOWN)
from sysstrndpxy import calculate_supertrend  # Structural engine (BUY / SELL / BULL / BEAR / SIDE)
from syscnfgpxy import TICKER
import pandas as pd

def get_entry_signal(df=None):
    """
    Advanced routing pipeline mapping structural trend regimes against execution signals.
    Exits follow live direction unconditionally. Entries utilize SuperTrend filtering, 
    while SIDE state lets direction flow through completely unfiltered.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Extract the geometric movement direction (UP / DOWN)
    direction, _ = get_signal(df)

    # 2. Extract the true SuperTrend regime matrix state (BUY / SELL / BULL / BEAR / SIDE)
    processed_df = calculate_supertrend(df)
    current_regime = str(processed_df['sma_trend_full'].iloc[-1]) # Last row state

    entry_signal = "NONE"
    
    # =========================================================================
    # UNCONDITIONAL EXIT MAPPING (Restored to your original engine rules)
    # =========================================================================
    exit_signal = "BULL" if direction == "UP" else "BEAR"

    # =========================================================================
    # ENTRY FILTER MATRIX & PRIORITY LAYER
    # =========================================================================
    
    # --- TIER 1 PRIORITY: ABSOLUTE CROSSOVER MOMENTS ---
    if current_regime == "BUY":
        entry_signal = "ATMBUY"
        
    elif current_regime == "SELL":
        entry_signal = "ATMSELL"

    # --- TIER 2 PRIORITY: PERSISTENT CONTINUATION STATES ---
    elif current_regime == "BULL":
        # Check alignment: Geometric engine says UP while SuperTrend is BULL
        if direction == "UP":
            entry_signal = "ATMBUY"   # Aligned -> Target ATM
        else:
            entry_signal = "BEAR"   # Misaligned / Protection Filter -> Target NTM

    elif current_regime == "BEAR":
        # Check alignment: Geometric engine says DOWN while SuperTrend is BEAR
        if direction == "DOWN":
            entry_signal = "ATMSELL"  # Aligned -> Target ATM
        else:
            entry_signal = "BULL"  # Misaligned / Protection Filter -> Target NTM

    # --- TIER 3 PRIORITY: SIDE CHOPPY REGIME (UNFILTERED BYPASS) ---
    elif current_regime == "SIDE":
        # SIDE should not filter anything. Let direction dictate execution completely.
        if direction == "UP":
            entry_signal = "ATMBUY"
        elif direction == "DOWN":
            entry_signal = "ATMSELL"

    # Console Status Reporting Actions
    if entry_signal != "NONE":
        print(f"       🔥 [ACTION REGIME] -> SuperTrend: {current_regime} | Direction: {direction}")
        print(f"       🔥 [ROUTING OUT]   -> ENTRY: {entry_signal} | EXIT: {exit_signal} 🔥")

    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL PROCESSED EXECUTION >> ENTRY: {entry} | EXIT: {ex}")
