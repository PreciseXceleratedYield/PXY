"""
===============================================================================
PXY OPTION ROUTING ENGINE: TWO-TIER UNIFIED ATM MASTER ROUTER
===============================================================================
Operational Matrix & Unified Token Routing Rules:
- TIER 1 (PRIMARY ABSOLUTE PRIORITY): 
  ATMBUY  -> Triggered ONLY on an exact active breakthrough CROSSOVER (BUY).
  ATMSELL -> Triggered ONLY on an exact active breakthrough CROSSOVER (SELL).

- TIER 2 (SECONDARY FIXED PRIORITY - UNIFIED): 
  ATMBUY  -> Triggered contextually when price is in the middle:
             Strictly ABOVE the 42 SMA AND Strictly BELOW the Supertrend (ST)
             AND SMA is BULL, ST is BEAR, and Entry is BUY.
             
  ATMSELL -> Triggered contextually when price is in the middle:
             Strictly BELOW the 42 SMA AND Strictly ABOVE the Supertrend (ST)
             AND SMA is BEAR, ST is BULL, and Entry is SELL.
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
    All successful route selections are unified strictly to ATM contract codes.
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
    # Checks for active crossover breakouts first to override all middle-zone signals
    if strnd_state == "BUY" or sma_state == "BUY":
        final_signal = "ATMBUY"
        return final_signal, exit_sig
        
    elif strnd_state == "SELL" or sma_state == "SELL":
        final_signal = "ATMSELL"
        return final_signal, exit_sig

    # ===============================================================================
    # 🔄 TIER 2: CONTEXTUAL MIDDLE ENTRY SIGNALS (STRICT SECOND PRIORITY)
    # ===============================================================================
    # Checked ONLY if no active crossover breakthrough is currently printing
    
    # 🟢 UNIFIED ATM BUY FLIP ZONE: Price is trapped in the middle
    if latest_close > latest_sma and latest_close < latest_st_line:
        if sma_state == "BULL" and strnd_state == "BEAR" and mkt_entry == "BUY":
            final_signal = "ATMBUY"
        
    # 🔴 UNIFIED ATM SELL FLIP ZONE: Price is trapped in the middle
    elif latest_close < latest_sma and latest_close > latest_st_line:
        if sma_state == "BEAR" and strnd_state == "BULL" and mkt_entry == "SELL":
            final_signal = "ATMSELL"

    return final_signal, exit_sig


if __name__ == "__main__":
    print("--- STARTING LIVE MULTI-SIGNAL CONTEXTUAL UNIFIED ATM ROUTER HUB ---")
    final_route, cascaded_exit = get_entry_signal(df=None)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY  : {final_route}")
    print(f"-> CASCADED EXIT : {cascaded_exit}\n")
