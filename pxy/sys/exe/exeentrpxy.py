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

import pandas as pd
import numpy as np

# Direct structural pipeline imports from your local engine modules
from sysstrndpxy import get_signal as get_strnd_signal
from syssmapxy import get_sma  # <--- Imported from your SMA script


def get_entry_signal(df=None):
    """Splits upstream ST signals into two paths: an unfiltered exit pipe

    and an SMA-filtered entry filter pipe mapping crossings to ATM/OTM tokens.
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

    # 3. SMA FILTER DATA EXTRACTION
    # Calculate SMA and extract latest price data for filtering
    sma_data = get_sma(target_df, period=42)
    sma_value = sma_data["value"]
    
    # Safely get the latest close price if dataframe exists and has data
    if target_df is not None and not target_df.empty and 'Close' in target_df.columns:
        latest_close = float(target_df['Close'].iloc[-1])
    else:
        latest_close = 0.0

    # Determine position relative to SMA (True if above or equal, False if below)
    is_above_sma = (latest_close >= sma_value) and (sma_data["status"] != "NA")

    # 4. FILTERED ENTRY ROUTING MATRIX WITH SMA CONDITIONALS
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
    
    # For production execution, ensure you pass your real dataframe here 
    # instead of None so get_sma can process the historical data.
    from sysdtafpxy import fetch_yf_data
    production_df = fetch_yf_data()
    
    final_route, cascaded_exit = get_entry_signal(df=production_df)

    print("\n⚡ PIPELINE DIAGNOSTICS:")
    print(f"-> FINAL ENTRY : {final_route}")
    print(f"-> CASCADED EXIT: {cascaded_exit}\n")


