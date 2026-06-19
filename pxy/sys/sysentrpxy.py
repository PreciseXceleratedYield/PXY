"""
===============================================================================
PXY OPTION ROUTING ENGINE: DIRECT EXCLUSIVE ST-ONLY ROUTER (SMA FILTERED)
===============================================================================
Operational Matrix:
- EXIT PIPE (Unfiltered): Exactly as received from Upstream ST
- ENTRY PIPE (Filtered): 
    - STRND: BUY  -> If Close >= SMA -> ATMBUY  | If Close < SMA -> OTMBUY
    - STRND: SELL -> If Close >= SMA -> OTMSELL | If Close < SMA -> ATMSELL
    - STRND: BULL -> BULL
    - STRND: BEAR -> BEAR
    - Otherwise   -> NONE
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
    from syssmapxy import get_sma
    from sysstrndpxy import get_signal as get_strnd_signal
except ModuleNotFoundError:
    try:
        # Fallback to absolute file spec handlers if implicit paths are locked by shell environment
        sma_spec = importlib.util.spec_from_file_location("syssmapxy", os.path.join(local_dir, "syssmapxy.py"))
        syssmapxy = importlib.util.module_from_spec(sma_spec)
        sma_spec.loader.exec_module(syssmapxy)
        get_sma = syssmapxy.get_sma

        strnd_spec = importlib.util.spec_from_file_location("sysstrndpxy", os.path.join(local_dir, "sysstrndpxy.py"))
        sysstrndpxy = importlib.util.module_from_spec(strnd_spec)
        strnd_spec.loader.exec_module(sysstrndpxy)
        get_strnd_signal = sysstrndpxy.get_signal
    except Exception as fatal_err:
        print(f"\n[CRITICAL] PLATFORM CORE IMPORT FAILURE: {fatal_err}")
        raise fatal_err


def get_entry_signal(df=None):
    """Splits upstream ST signals into two paths: an unfiltered exit pipe

    and an SMA-filtered entry filter pipe mapping crossings to ATM/OTM tokens.
    """
    # 3. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINE
    target_df = pd.DataFrame() if df is None else df

    # Pull the raw, unfiltered structural strategy signal directly from your corrected module
    raw_strnd_signal = str(get_strnd_signal(target_df)).strip()
    
    # Standardize string format for entry conditional matching logic
    strnd_state = raw_strnd_signal.upper()

    # 4. UNFILTERED CASCADED EXIT PIPE
    # Passes the upstream token out completely as-is, with no alterations
    exit_sig = raw_strnd_signal

    # 5. SMA CO-LOCATED FILTER MATRIX CALCULATIONS
    sma_data = get_sma(target_df, period=42)
    sma_value = sma_data["value"]
    
    # Extract the correct index row alignment matching your ST engine (n-2 for confirmed close)
    if target_df is not None and not target_df.empty and 'Close' in target_df.columns:
        if len(target_df) >= 2:
            latest_close = float(target_df['Close'].iloc[-2]) # ⚡ Tied directly to same candle as get_signal
        else:
            latest_close = float(target_df['Close'].iloc[-1])
    else:
        latest_close = 0.0

    # Determine position relative to SMA (True if above or equal, False if below)
    is_above_sma = (latest_close >= sma_value) and (sma_data["status"] != "NA")

    # 6. FILTERED ENTRY ROUTING MATRIX WITH SMA CONDITIONALS
    if strnd_state == "BUY":
        final_signal = "ATMBUY" if is_above_sma else "OTMBUY"
        
    elif strnd_state == "SELL":
        final_signal = "OTMSELL" if is_above_sma else "ATMSELL"
        
    elif strnd_state in ["BULL", "BEAR"]:
        final_signal = strnd_state
        
    else:
        final_signal = "NONE"

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



