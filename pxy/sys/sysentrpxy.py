"""
===============================================================================
PXY OPTION ROUTING ENGINE: DIRECT EXCLUSIVE ST-ONLY ROUTER (ATM / ATM)
===============================================================================
Operational Matrix (Strict Priority Filter Rule Set):
- STRND: BUY  -> ENTRY: ATMBUY   | EXIT: From Upstream ST (Priority Trigger)
- STRND: SELL -> ENTRY: ATMSELL  | EXIT: From Upstream ST (Priority Trigger)
- STRND: BULL -> ENTRY: NONE     | EXIT: From Upstream ST (Priority Trigger)
- STRND: BEAR -> ENTRY: NONE     | EXIT: From Upstream ST (Priority Trigger)
===============================================================================
"""

import pandas as pd

# Direct structural pipeline imports from your local engine modules
from sysstrndpxy import get_signal as get_strnd_signal


def get_entry_signal(df=None):
    """Combines inputs from strndpxy to calculate the direct option routing tokens,

    matched 1:1 for execution framework compatibility.
    """
    # 1. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINES
    target_df = pd.DataFrame() if df is None else df

    # Pull structural strategy signals directly
    strnd_state = str(get_strnd_signal(target_df)).upper().strip()

    # 2. ASSIGN UNALTERED CASCADED EXIT SIGNAL FROM UPSTREAM ST
    # Directly map exit triggers to the raw, unfiltered upstream ST states
    if strnd_state in ["SELL", "BEAR"]:
        exit_sig = "BUY"
    elif strnd_state in ["BUY", "BULL"]:
        exit_sig = "SELL"
    else:
        exit_sig = "NONE"

    # 3. EXCLUSIVE PRIORITY FILTER ROUTING MATRIX (ST-ONLY)
    # Priority 1: Direct Active Crossing Signals from your strategy engine
    if strnd_state == "BUY":
        final_signal = "ATMBUY"
    elif strnd_state == "SELL":
        final_signal = "ATMSELL"

    # Priority 2: Standard Trend Regimes (No executions on continuation bars)
    elif strnd_state in ["BULL", "BEAR"]:
        final_signal = "NONE"

    # Default fallback protection
    else:
        final_signal = "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    print("--- STARTING LIVE ST-ONLY EXCLUSIVE ROUTER HUB ---")
    final_route, cascaded_exit = get_entry_signal(df=None)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY : {final_route}")
    print(f"-> CASCADED EXIT: {cascaded_exit}\n")

