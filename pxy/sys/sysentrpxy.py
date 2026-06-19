"""""
===============================================================================
PXY OPTION ROUTING ENGINE: DIRECT EXCLUSIVE ROUTER HUB (MKT PXY ATM INTEGRATED)
===============================================================================
Operational Matrix:
- EXIT PIPE (Unfiltered): Exactly as received from Upstream sysmktpxy
- ENTRY PIPE (Filtered): 
    - MKT_SIGNAL: BUY  -> ATMBUY
    - MKT_SIGNAL: SELL -> ATMSELL
    - Otherwise        -> As-Is from Upstream
===============================================================================
"""

import os
import sys
import importlib.util
import numpy as np
import pandas as pd

# 1. RUNTIME ENGINE SAME-DIRECTORY PATH ALIGNMENT
# Pin search context explicitly to its own location to handle isolated automation runners
local_dir = os.path.dirname(os.path.abspath(__file__))
if local_dir not in sys.path:
    sys.path.insert(0, local_dir)

# 2. ROBUST PIPELINE IMPORTS WITH EXPLICIT BACKUPS (ONLY MKT PXY)
try:
    from sysmktpxy import get_signal as get_mktpxy_signal

except ModuleNotFoundError:
    try:
        # Fallback to absolute file spec handlers if implicit paths are locked by shell environment
        mktpxy_spec = importlib.util.spec_from_file_location("sysmktpxy", os.path.join(local_dir, "sysmktpxy.py"))
        sysmktpxy = importlib.util.module_from_spec(mktpxy_spec)
        mktpxy_spec.loader.exec_module(sysmktpxy)
        get_mktpxy_signal = sysmktpxy.get_signal
    except Exception as fatal_err:
        print(f"\n[CRITICAL] PLATFORM CORE IMPORT FAILURE: {fatal_err}")
        raise fatal_err


def get_entry_signal(df=None):
    """Sources signals from sysmktpxy. Passes the exit pipe unfiltered,

    and filters the entry pipe by mapping BUY/SELL strictly to ATM tokens.
    """
    # 3. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINE
    target_df = pd.DataFrame() if df is None else df

    # 4. FETCH SIGNALS FROM THE IMPORTED sysmktpxy ENGINE DIRECTLY
    try:
        # Extracts raw entry and exit streams natively from your module
        mktpxy_entry, mktpxy_exit = get_mktpxy_signal(target_df)
        
        # Standardize strings for accurate evaluation
        raw_entry = str(mktpxy_entry).upper().strip()
        
        # 5. UNFILTERED CASCADED EXIT PIPE
        exit_sig = str(mktpxy_exit).strip()

        # 6. ENTRY PIPE: BUY/SELL ATM REWRITE MATRIX
        if raw_entry == "BUY":
            final_signal = "ATMBUY"
        elif raw_entry == "SELL":
            final_signal = "ATMSELL"
        else:
            final_signal = str(mktpxy_entry).strip() # Keeps BULL, BEAR, NONE, etc. completely untouched

    except Exception:
        final_signal = "NONE"
        exit_sig = "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    print("--- STARTING LIVE ST-ONLY EXCLUSIVE ROUTER HUB WITH SMA ---")
    
    # Attempt to locate and pull data frame matrix from your data pipeline utility
    try:
        if os.path.exists(os.path.join(local_dir, "sysdtafpxy.py")):
            dta_spec = importlib.util.spec_from_file_location("sysdtafpxy", os.path.join(local_dir, "sysdtafpxy.py"))
            sysdtafpxy = importlib.util.module_from_spec(dta_spec)
            dta_spec.loader.exec_module(sysdtafpxy)
            fetch_yf_data = sysdtafpxy.fetch_yf_data
        else:
            from sysdtafpxy import fetch_yf_data
            
        production_df = fetch_yf_data()
    except Exception:
        print("[WARNING] sysdtafpxy module unavailable. Sourcing empty matrix.")
        production_df = None
        
    final_route, cascaded_exit = get_entry_signal(df=production_df)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY : {final_route}")
    print(f"-> CASCADED EXIT: {cascaded_exit}\n")



