# sysentrpxy.py
"""
===============================================================================
PXY EXECUTION OPTION ROUTING ENGINE WITH IST TIME-WINDOW CONTROLS
===============================================================================
Timezone Configuration: Aligned strictly to Indian Standard Time (IST) Zone.

Operational Rules Matrix (Indian Markets):
1. SIMPLIFIED ATM RULE ONLY: All entry signals and breakout crossovers 
   route exclusively to ATM contracts (ATMBUY / ATMSELL) for baseline testing.
===============================================================================
"""

import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from syscnfgpxy import TICKER

# Ingestion gateways from your exact strategy matrix modules
from sysmktpxy import get_signal, CHECK_CONFIRMED_ONLY
from sysstrndpxy import calculate_supertrend

def get_entry_signal(df=None):
    # 1. Fetch the raw, unfiltered Heikin-Ashi candle state maps from sysmktpxy
    mkt_entry, exit_sig = get_signal(df)

    # Clean and standardize incoming string formats to avoid whitespace anomalies
    mkt_entry = str(mkt_entry).upper().strip()
    exit_sig  = str(exit_sig).upper().strip()

    # 2. Extract the underlying baseline macro trend and multi-interval signal markers
    strnd_df = calculate_supertrend(df=None)
    
    macro_trend = "NEUTRAL"
    cross_event = "NONE"

    if strnd_df is not None and not strnd_df.empty:
        # Align lookup index to match your switch state (Confirmed vs Live Running)
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        
        try:
            # Point to unified Capitalized Column mapping matching cross-module updates
            macro_trend = str(strnd_df['ST_Trend'].iloc[idx]).upper().strip()
            cross_event = str(strnd_df['st_signal_full'].iloc[idx]).upper().strip()
        except Exception:
            pass

    # 3. Establish Base Current Time in Indian Standard Time (IST)
    tz_ist = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(tz_ist).time()

    # Parse dataframe time if present to ensure proper sync with tracking data
    if strnd_df is not None and not strnd_df.empty:
        try:
            last_timestamp = strnd_df.index[-1]
            if not isinstance(last_timestamp, pd.Timestamp):
                last_timestamp = pd.to_datetime(last_timestamp)
            
            if last_timestamp.tzinfo is not None:
                current_time_ist = last_timestamp.astimezone(tz_ist).time()
            else:
                current_time_ist = last_timestamp.time()
        except Exception:
            pass

    final_signal = "NONE"

    # 4. FLAT ATM OPTIONS ROUTING MATRIX
    # Priority 1: Multi-Interval Breakout Indicators
    if "BB" in cross_event or "MB" in cross_event or "CB" in cross_event:
        final_signal = "ATMBUY"
    elif "BS" in cross_event or "MS" in cross_event or "CS" in cross_event:
        final_signal = "ATMSELL"
        
    # Priority 2: Raw Candle Signals / Inbound Reversals
    elif exit_sig == "BUY":
        final_signal = "ATMBUY"
    elif exit_sig == "SELL":
        final_signal = "ATMSELL"
        
    # Priority 3: Fallback Pass-Through 
    elif mkt_entry in ["BUY", "BULL"]:
        final_signal = "ATMBUY"
    elif mkt_entry in ["SELL", "BEAR"]:
        final_signal = "ATMSELL"
    else:
        final_signal = "NONE"

    # Reporting on active Indian Market signals
    if final_signal in ["ATMBUY", "ATMSELL", "BUY", "SELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    return final_signal, exit_sig

if __name__ == "__main__":
    print("\n[PXY ROUTER STATUS] Option Route Verification Matrix Active.")
    print("-" * 50)
    final_route, raw_exit = get_entry_signal(df=None)
    print("-" * 50)
    print(f"FINAL DECISION >> ROUTE STATUS: {final_route} | RAW CANDLE FLIP: {raw_exit}")

