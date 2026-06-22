# Save this file as sysoptrouterpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE: MULTI-MODE ROUTER HUB (MKT-RAW / STRND-SMA-CONDITION)
===============================================================================
Operational Matrix:

[MODE = RAW] -> Directional Pass-Through (Sourced 100% from sysmktpxy)
- EXIT PIPE  (Normalized): Sourced from raw upstream market exit, outputs BULL or BEAR
- ENTRY PIPE : Sourced from raw upstream entry
               - BUY BULL -> ATMBUY  (Long Entry)
               - SELL BEAR -> ATMSELL (Short Entry)
               - Otherwise -> NONE

[MODE = CONDITION] -> Legacy Ruleset (Sourced from Upstream ST + 42-SMA Filter)
- EXIT PIPE  (Unfiltered): Sourced from Upstream ST, outputs BULL or BEAR
- ENTRY PIPE (Dynamic Delta Allocation): 
    - STRND: BULL AND SMA: NORTH -> ATMBUY  (Matched Trend / Higher Delta)
    - STRND: BULL AND SMA: SOUTH -> OTMBUY  (Counter Trend / Lower Delta)
    - STRND: BEAR AND SMA: SOUTH -> ATMSELL (Matched Trend / Higher Delta)
    - STRND: BEAR AND SMA: NORTH -> OTMSELL (Counter Trend / Lower Delta)
    - Otherwise                  -> NONE
===============================================================================
"""

import os
import sys
import importlib.util
import numpy as np
import pandas as pd

# Global Switch Layer: Choose "RAW" or "CONDITION"
MODE = "CONDITION"

# 1. RUNTIME ENGINE SAME-DIRECTORY PATH ALIGNMENT
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

# Import your binary 42-SMA engine function
try:
    from syssmapxy import get_sma
except ModuleNotFoundError:
    print("\n[CRITICAL] syssmapxy.py engine module missing from local directory.")
    raise

# Dynamic Import for Clean RAW Mode
try:
    from sysmktpxy import get_signal as get_mktpxy_signal
except ModuleNotFoundError:
    get_mktpxy_signal = None


def get_entry_signal(df=None):
    """Processes upstream ST signals, standardizes tokens to BULL/BEAR,

    checks alignment with 42-SMA, and routes to ATM or OTM option types.
    """
    # 3. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINE
    target_df = pd.DataFrame() if df is None else df

    # =========================================================================
    # PIPELINE VARIANT: CLEAN RAW MODE (Sourced cleanly from sysmktpxy)
    # =========================================================================
    if MODE == "RAW":
        if get_mktpxy_signal is None:
            print("\n[CRITICAL] sysmktpxy.py module missing from local directory.")
            return "NONE", "NONE"
            
        raw_entry, raw_exit = get_mktpxy_signal(target_df)
        
        # Clean text inputs for consistent string matching
        raw_entry_clean = str(raw_entry).strip().upper()
        raw_exit_clean = str(raw_exit).strip().upper()
        
        # A. ENTRY ROUTING MATRIX
        if raw_entry_clean in ["BUY BULL", "BUY", "BULL"]:
            final_signal = "ATMBUY"
        elif raw_entry_clean in ["SELL BEAR", "SELL", "BEAR"]:
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"
            
        # B. EXIT ROUTING MATRIX (CONSOLIDATE TO PURE BULL / BEAR)
        if raw_exit_clean in ["BUY BULL", "BUY", "BULL"]:
            exit_sig = "BULL"
        elif raw_exit_clean in ["SELL BEAR", "SELL", "BEAR"]:
            exit_sig = "BEAR"
        else:
            exit_sig = "NONE"
            
        return final_signal, exit_sig

    # =========================================================================
    # ORIGINAL PIPELINE: CONDITION MODE (100% Untouched Legacy Code Block)
    # =========================================================================
    # Pull the raw, unfiltered structural strategy signal
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

    # 6. RUN THE 42-SMA DIRECTIONAL FILTERING ENGINE
    sma_result = get_sma(target_df, period=42)
    sma_direction = sma_result.get("status", "NA") # "NORTH" or "SOUTH"

    # 7. ROUTING MATRIX FOR ATM AND OTM SEGREGATION
    if normalized_signal == "BULL":
        if sma_direction == "NORTH":
            final_signal = "ATMBUY"   # Trend Aligned
        else:
            final_signal = "OTMBUY"   # Counter-Trend Protection
            
    elif normalized_signal == "BEAR":
        if sma_direction == "SOUTH":
            final_signal = "ATMSELL"  # Trend Aligned
        else:
            final_signal = "OTMSELL"  # Counter-Trend Protection
            
    else:
        final_signal = "NONE"

    return final_signal, exit_sig


if __name__ == "__main__":
    print(f"--- STARTING LIVE ST-ONLY EXCLUSIVE ROUTER HUB [MODE: {MODE}] ---")
    
    # Attempt to locate and pull data frame matrix
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

