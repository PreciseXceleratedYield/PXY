"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX & REGIME PRIORITY
===============================================================================
Operational Rules Matrix:
1. FIRST PRIORITY : Fresh triggers ('BUY' / 'SELL') -> Keep ATM strikes.
2. SECOND PRIORITY: Continuous trends ('BULL' / 'BEAR') -> Check alignment with get_signal.
                    - Aligned (BULL+UP / BEAR+DOWN) -> Keep ATM strikes.
                    - Misaligned (BULL+DOWN / BEAR+UP) -> Downgrade to NTM strikes.
===============================================================================
"""

# Import the signal functions from your engines
from sysmktpxy import get_signal      # Direction engine (UP / DOWN)
from sysstrndpxy import calculate_supertrend  # Structural engine (BUY / SELL / BULL / BEAR)
from syscnfgpxy import TICKER
import pandas as pd

def get_entry_signal(df=None):
    """
    Advanced routing pipeline mapping structural trend regimes against execution signals.
    Returns: entry_signal (ATMBUY, NTMBUY, ATMSELL, NTMSELL, NONE) and exit_signal.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Extract the geometric movement direction (UP / DOWN)
    direction, _ = get_signal(df)

    # 2. Extract the true SuperTrend regime matrix state (BUY / SELL / BULL / BEAR)
    processed_df = calculate_supertrend(df)
    current_regime = str(processed_df['sma_trend_full'].iloc[-1]) # Last row state

    entry_signal = "NONE"
    exit_signal = "NONE"

    # =========================================================================
    # CRITICAL EXECUTION MATRIX & PRIORITY LAYER
    # =========================================================================
    
    # --- TIER 1 PRIORITY: ABSOLUTE CROSSOVER MOMENTS ---
    if current_regime == "BUY":
        entry_signal = "ATMBUY"
        exit_signal = "BULL"
        
    elif current_regime == "SELL":
        entry_signal = "ATMSELL"
        exit_signal = "BEAR"

    # --- TIER 2 PRIORITY: PERSISTENT CONTINUATION STATES ---
    elif current_regime == "BULL":
        exit_signal = "BULL"
        # Check alignment: Geometric engine says UP while SuperTrend is BULL
        if direction == "UP":
            entry_signal = "ATMBUY"   # Aligned -> Target ATM
        else:
            entry_signal = "NTMBUY"   # Misaligned / Protection Filter -> Target NTM

    elif current_regime == "BEAR":
        exit_signal = "BEAR"
        # Check alignment: Geometric engine says DOWN while SuperTrend is BEAR
        if direction == "DOWN":
            entry_signal = "ATMSELL"  # Aligned -> Target ATM
        else:
            entry_signal = "NTMSELL"  # Misaligned / Protection Filter -> Target NTM

    # Console Status Reporting Actions
    if entry_signal != "NONE":
        print(f"     🔥 SUPER: {current_regime} | MOVE: {direction}")
        print(f"     🔥 ENTRY: {entry_signal} | EXIT: {exit_signal}")

    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL PROCESSED EXECUTION >> ENTRY: {entry} | EXIT: {ex}")



