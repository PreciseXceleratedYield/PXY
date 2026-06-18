"""
===============================================================================
PXY OPTION ROUTING ENGINE: DIRECT EXCLUSIVE MULTI-SIGNAL ROUTER (ATM / ATM)
===============================================================================
Operational Matrix (Strict Priority Filter Rule Set):
- STRND: BUY  -> ENTRY: ATMBUY   | EXIT: From Upstream (Priority Trigger)
- STRND: SELL -> ENTRY: ATMSELL  | EXIT: From Upstream (Priority Trigger)
- STRND: BULL -> ENTRY: ATMBUY if MKTPXY Entry == "BUY" else NONE
- STRND: BEAR -> ENTRY: ATMSELL if MKTPXY Entry == "SELL" else NONE
===============================================================================
"""

import pandas as pd

# Direct structural pipeline imports from your local engine modules
from sysstrndpxy import get_signal as get_strnd_signal
from sysmktpxy import get_signal as get_mkt_signals


def get_entry_signal(df=None):
    """Combines inputs from strndpxy and mktpxy to calculate the direct 

    option routing tokens, matched 1:1 for execution framework compatibility.
    """
    # 1. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINES
    target_df = pd.DataFrame() if df is None else df

    # Pull structural strategy signals directly
    strnd_state = str(get_strnd_signal(target_df)).upper().strip()

    # Pull ingestion matrix signals directly (Straight take unpacker)
    mkt_entry, mkt_exit = get_mkt_signals(target_df)
    mkt_entry = str(mkt_entry).upper().strip()
    mkt_exit = str(mkt_exit).upper().strip()

    # 2. ASSIGN UNALTERED CASCADED EXIT SIGNAL
    # Explicitly leaves the exit signal from upstream completely as-is
    exit_sig = mkt_exit

    # 3. EXCLUSIVE PRIORITY FILTER ROUTING MATRIX
    # Priority 1: Direct Active Crossing Signals from your strategy engine
    if strnd_state == "BUY":
        final_signal = "ATMBUY"
    elif strnd_state == "SELL":
        final_signal = "ATMSELL"

    # Priority 2: Filtered Trend Regimes matched against mktpxy entry tokens
    elif strnd_state == "BULL":
        final_signal = "ATMBUY" if mkt_entry == "BUY" else "NONE"
    elif strnd_state == "BEAR":
        final_signal = "ATMSELL" if mkt_entry == "SELL" else "NONE"

    # Default fallback protection
    else:
        final_signal = "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    print("--- STARTING LIVE MULTI-SIGNAL EXCLUSIVE ROUTER HUB ---")
    final_route, cascaded_exit = get_entry_signal(df=None)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY : {final_route}")
    print(f"-> CASCADED EXIT: {cascaded_exit}\n")


