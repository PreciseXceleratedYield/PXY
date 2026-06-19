"""
===============================================================================
PXY OPTION ROUTING ENGINE: TWO-TIER SMA BOUNDARY COMPASS MASTER ROUTER
===============================================================================
Operational Matrix & Absolute SMA Boundary Filters:
- GLOBAL HARD BIAS GATES:
  * ATMBUY is ONLY allowed if Close > 42 SMA. Otherwise, forces NONE.
  * ATMSELL is ONLY allowed if Close < 42 SMA. Otherwise, forces NONE.

- EXPLICIT CANCELLATION BLOCKS (FORCED TO NONE):
  * A downside cross below ST that happens ABOVE the SMA becomes NONE.
  * An upside cross above ST that happens BELOW the SMA becomes NONE.
===============================================================================
"""

import pandas as pd
import numpy as np

# Direct structural pipeline imports from your local engine modules
from sysstrndpxy import get_signal as get_strnd_signal, calculate_supertrend
from sysmktpxy import get_signal as get_mkt_signals
from syssmapxy import get_sma as get_sma_signal


def get_entry_signal(df=None):
    """
    Calculates 1:1 option routing tokens. Enforces crossovers as absolute 
    first priority, and strictly aligned middle-zone entries as second priority.
    All paths pass through an absolute SMA filtering barrier before release.
    """
    # 1. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINES
    target_df = pd.DataFrame() if df is None else df.copy()

    # Pull structural strategy signals directly
    strnd_state = str(get_strnd_signal(target_df)).upper().strip()
    
    # Pull SMA engine analytics and extract values
    sma_data = get_sma_signal(target_df, period=42)
    sma_state = str(sma_data.get("status", "NA")).upper().strip()
    
    # Process full DataFrame structures to extract exact line metrics for the flip logic
    st_df = calculate_supertrend(target_df)
    
    # Safeguard against cold starts or empty data feeds
    if st_df.empty or 'src_c' not in st_df.columns or 'pxy_st_line' not in st_df.columns:
        return "NONE", "NONE"
        
    latest_close   = float(st_df['src_c'].iloc[-1])
    latest_st_line = float(st_df['pxy_st_line'].iloc[-1])
    latest_sma     = float(sma_data.get("value", 0.0))

    # Pull ingestion matrix signals directly
    mkt_entry, mkt_exit = get_mkt_signals(target_df)
    mkt_entry = str(mkt_entry).upper().strip()

    # 2. ASSIGN UNALTERED CASCADED EXIT SIGNAL
    exit_sig = str(mkt_exit).upper().strip()

    # Initialize default response token to NONE
    final_signal = "NONE"

    # ===============================================================================
    # 📡 TIER 1: CROSSOVER BREAKOUT TRIGGERS (ABSOLUTE FIRST PRIORITY)
    # ===============================================================================
    # Checks for active crossover breakouts first
    if strnd_state == "BUY" or sma_state == "BUY":
        final_signal = "ATMBUY"
        
    elif strnd_state == "SELL" or sma_state == "SELL":
        final_signal = "ATMSELL"

    # ===============================================================================
    # 🔄 TIER 2: CONTEXTUAL MIDDLE ENTRY SIGNALS (SECONDARY PRIORITY)
    # ===============================================================================
    # Checked ONLY if no active crossover breakthrough was captured above
    else:
        # 🟢 UNIFIED ATM BUY FLIP ZONE: Price is trapped in the middle
        if latest_close > latest_sma and latest_close < latest_st_line:
            if sma_state == "BULL" and strnd_state == "BEAR" and mkt_entry == "BUY":
                final_signal = "ATMBUY"
            
        # 🔴 UNIFIED ATM SELL FLIP ZONE: Price is trapped in the middle
        elif latest_close < latest_sma and latest_close > latest_st_line:
            if sma_state == "BEAR" and strnd_state == "BULL" and mkt_entry == "SELL":
                final_signal = "ATMSELL"

    # ===============================================================================
    # ⛔ CRITICAL STEP 4: ABSOLUTE SMA PHYSICAL LOCATION GATING OVERRIDES
    # ===============================================================================
    # Enforces the absolute baseline rules. Intercepts and blocks invalid spatial crosses.
    
    if final_signal == "ATMBUY":
        # Block buy if price is physically located below the 42 SMA threshold line
        # Covers the case: "cross above ST and below SMA becomes NONE"
        if latest_close <= latest_sma:
            final_signal = "NONE"

    elif final_signal == "ATMSELL":
        # Block sell if price is physically located above the 42 SMA threshold line
        # Covers the case: "cross below ST and above SMA becomes NONE"
        if latest_close >= latest_sma:
            final_signal = "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    print("--- STARTING LIVE MULTI-SIGNAL CONTEXTUAL SMA BOUNDARY ROUTER HUB ---")
    final_route, cascaded_exit = get_entry_signal(df=None)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY  : {final_route}")
    print(f"-> CASCADED EXIT : {cascaded_exit}\n")

