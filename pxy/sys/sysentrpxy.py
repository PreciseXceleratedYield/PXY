"""""
===============================================================================
PXY OPTION ROUTING ENGINE: DIRECT EXCLUSIVE ST-ONLY ROUTER (CONSOLIDATED ST)
===============================================================================
Operational Matrix:
- EXIT PIPE (Unfiltered): Sourced from Upstream ST, outputs BULL or BEAR
- ENTRY PIPE (Filtered): 
    - STRND: BUY / BULL  -> ATMBUY
    - STRND: SELL / BEAR -> ATMSELL
    - Otherwise          -> NONE
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

# 2. ROBUST PIPELINE IMPORTS WITH EXPLICIT BACKUPS
try:
    from sysatrndpxy import get_atrnd_signal as get_signal

except ModuleNotFoundError:
    try:
        strnd_spec = importlib.util.spec_from_file_location("sysstrndpxy", os.path.join(local_dir, "sysstrndpxy.py"))
        sysstrndpxy = importlib.util.module_from_spec(strnd_spec)
        strnd_spec.loader.exec_module(sysstrndpxy)
        get_signal = sysstrndpxy.get_signal
    except Exception as fatal_err:
        print(f"\n[CRITICAL] PLATFORM CORE IMPORT FAILURE: {fatal_err}")
        raise fatal_err


def get_entry_signal(df=None):
    """Processes upstream ST signals, standardizes tokens to BULL/BEAR,

    and splits them into an unfiltered exit pipe and an ATM entry pipe.
    """
    # 3. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINE
    target_df = pd.DataFrame() if df is None else df

    # Pull the raw, unfiltered structural strategy signal directly from your corrected module
    raw_strnd_signal = str(get_signal(target_df)).strip().upper()

    # 4. CONSOLIDATE UPSTREAM TOKENS TO PURE BULL / BEAR
    if raw_strnd_signal in ["BUY", "BULL"]:
        normalized_signal = "BULL"
    elif raw_strnd_signal in ["SELL", "BEAR"]:
        normalized_signal = "BEAR"
    else:
        normalized_signal = "NONE"

    # 5. UNFILTERED CASCADED EXIT PIPE
    exit_sig = normalized_signal

    # 6. FILTERED ENTRY ROUTING MATRIX MAPPED TO ATM TOKENS
    if normalized_signal == "BULL":
        final_signal = "ATMBUY"
    elif normalized_signal == "BEAR":
        final_signal = "ATMSELL"
    else:
        final_signal = "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    print("--- STARTING LIVE ST-ONLY EXCLUSIVE ROUTER HUB ---")
    
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


