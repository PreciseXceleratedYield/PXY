"""
===============================================================================
PXY OPTION ROUTING ENGINE: DIRECT EXCLUSIVE ST-ONLY ROUTER (ATM / ATM)
===============================================================================
Operational Matrix:
- EXIT PIPE (Unfiltered): Exactly as received from Upstream ST
- ENTRY PIPE (Filtered): 
    - STRND: BUY  -> ATMBUY
    - STRND: SELL -> ATMSELL
    - STRND: BULL -> BULL
    - STRND: BEAR -> BEAR
    - Otherwise   -> NONE
===============================================================================
"""

import pandas as pd

# Direct structural pipeline imports from your local engine modules
from sysstrndpxy import get_signal as get_strnd_signal


def get_entry_signal(df=None):
    """Splits upstream ST signals into two paths: an unfiltered exit pipe

    and an ATM entry filter pipe mapping crossings to ATM tokens and trends to regimes.
    """
    # 1. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINE
    target_df = pd.DataFrame() if df is None else df

    # Pull the raw, unfiltered structural strategy signal directly
    raw_strnd_signal = str(get_strnd_signal(target_df)).strip()
    
    # Standardize string format for entry conditional matching logic
    strnd_state = raw_strnd_signal.upper()

    # 2. UNFILTERED CASCADED EXIT PIPE
    # Passes the upstream token out completely as-is, with no alterations
    exit_sig = raw_strnd_signal

    # 3. FILTERED ENTRY ROUTING MATRIX
    # Converts crossings to execution tokens, retains trend regimes, defaults to NONE
    if strnd_state == "BUY":
        final_signal = "ATMBUY"
    elif strnd_state == "SELL":
        final_signal = "ATMSELL"
    elif strnd_state in ["BULL", "BEAR"]:
        final_signal = strnd_state
    else:
        final_signal = "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    print("--- STARTING LIVE ST-ONLY EXCLUSIVE ROUTER HUB ---")
    final_route, cascaded_exit = get_entry_signal(df=None)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY : {final_route}")
    print(f"-> CASCADED EXIT: {cascaded_exit}\n")


