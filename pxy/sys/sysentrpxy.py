"""
===============================================================================
PXY EXECUTION OPTION ROUTING ENGINE WITH UNIFIED PIPELINE AND TREND CROSS OVER FILTERS
===============================================================================
Operational Rules Matrix:
1. BULL / BEAR States: Bypasses filters and passes down unconditionally.
2. Crossovers & Trend Alignment (BUY, SELL, NORTH, SOUTH): Maps to OTMBUY / OTMSELL.
3. Unaligned States: Falls back defensively to AVGBUY / AVGSELL.
4. Exit Pipeline: Left alone completely as raw state (no transformations).
===============================================================================
"""

from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

def get_entry_signal(df=None):
    # 1. Fetch Synced Signals from our confirmed sysmktpxy pipeline
    # Note: engine returns identical states for both variables due to the unified pipeline
    entry_l4, exit_l2 = get_signal(df)

    # 2. Establish Time Metrics for Logging/Sync Verification (IST Zone)
    tz_ist = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(tz_ist).time()

    if df is not None and not df.empty:
        try:
            last_timestamp = df.index[-1]
            if not isinstance(last_timestamp, pd.Timestamp):
                last_timestamp = pd.to_datetime(last_timestamp)
            
            if last_timestamp.tzinfo is not None:
                current_time_ist = last_timestamp.astimezone(tz_ist).time()
            else:
                current_time_ist = last_timestamp.time()
        except Exception:
            pass

    final_signal = "NONE"

    # 3. UNCONDITIONAL PASS-THROUGH FOR CONTINUATION STATES
    if entry_l4 in ["BULL", "BEAR"]:
        final_signal = entry_l4

    # 4. TREND-ALIGNED & CROSSOVER PASS TO OTM
    elif entry_l4 in ["BUY", "NORTH"]:
        final_signal = "OTMBUY"
    elif entry_l4 in ["SELL", "SOUTH"]:
        final_signal = "OTMSELL"

    # 5. DEFENSIVE FALLBACK LAYER FOR UNALIGNED STATES (AVG STRATEGY)
    else:
        if entry_l4 in ["NONE", ""] and exit_l2 in ["BUY", "NORTH"]:
            final_signal = "AVGBUY"
        elif entry_l4 in ["NONE", ""] and exit_l2 in ["SELL", "SOUTH"]:
            final_signal = "AVGSELL"
        else:
            final_signal = "AVGSELL"  # Safe system default for absolute structural compliance

    # Console Status Reporting
    if final_signal in ["OTMBUY", "OTMSELL", "AVGBUY", "AVGSELL", "BULL", "BEAR"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    # Returns processed final_signal and completely untouched raw exit_l2
    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")



