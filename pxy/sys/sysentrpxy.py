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
import numpy as np
import pandas as pd

# 1. ENFORCE LOCAL DIRECTORY LOOKUP FOR CO-LOCATED IMPORTS
# Gets the exact folder where this script lives and places it at the front of Python's search path
local_dir = os.path.dirname(os.path.abspath(__file__))
if local_dir not in sys.path:
    sys.path.insert(0, local_dir)

# 2. FRAMEWORK PIPELINE ENGINE IMPORTS
try:
    from syssmapxy import get_sma
    from sysstrndpxy import get_signal as get_strnd_signal
except ModuleNotFoundError as e:
    print(f"\n[CRITICAL] SAME-DIRECTORY IMPORT FAILURE: {e}")
    print(f"[DEBUG] Local execution directory: {local_dir}")
    print("[DEBUG] Files currently visible inside this folder:")
    try:
        for file in os.listdir(local_dir):
            if file.endswith('.py'):
                print(f" -> {file}")
    except Exception as read_err:
        print(f" -> Could not list folder contents: {read_err}")
    raise e


def get_entry_signal(df=None):
    """Splits upstream ST signals into two paths: an unfiltered exit pipe
    and an SMA-filtered entry filter pipe mapping crossings to ATM/OTM tokens.
    """
    # 3. DIRECT INGESTION FROM UPSTREAM SOURCE PIPELINE
    target_df = pd.DataFrame() if df is None else df

    # Pull the raw, unfiltered structural strategy signal directly
    raw_strnd_signal = str(get_strnd_signal(target_df)).strip()

    # Standardize string format for entry conditional matching logic
    strnd_state = raw_strnd_signal.upper()

    # 4. UNFILTERED CASCADED EXIT PIPE
    exit_sig = raw_strnd_signal

    # 5. SMA FILTER DATA EXTRACTION
    sma_data = get_sma(target_df, period=42)
    sma_value = sma_data["value"]

    # Safely get the latest close price if dataframe contains execution history
    if target_df is not None and not target_df.empty and "Close" in target_df.columns:
        latest_close = float(target_df["Close"].iloc[-1])
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

    # Sync with live historical engine frame safely via your data fetcher
    try:
        from sysdtafpxy import fetch_yf_data
        production_df = fetch_yf_data()
    except ModuleNotFoundError:
        print("[WARNING] sysdtafpxy data module not found. Falling back to empty test frame.")
        production_df = None

    final_route, cascaded_exit = get_entry_signal(df=production_df)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY : {final_route}")
    print(f"-> CASCADED EXIT: {cascaded_exit}\n")


