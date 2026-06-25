"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX
===============================================================================
Operational Rules Matrix:
1. BULL / BEAR Candlesticks: Passes downstream unconditionally without conversion.
2. Trend Engine BUY / SELL: Ultimate priority route, maps straight to OTM.
3. Market Engine BUY / SELL: Maps to OTM if Trend is aligned, else falls back to AVG.
===============================================================================
"""

from sysmktpxy import get_signal as get_market_shape
from sysstrndpxy import get_signal as get_trend_state
from syscnfgpxy import TICKER
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

def get_entry_signal(df=None):
    # 1. Fetch market candle geometry and macro 42 SMA trends independently
    mkt_entry, exit_l2 = get_market_shape(df)
    trend_entry, _ = get_trend_state(df)  # Returns BUY, SELL, NORTH, SOUTH from 42 SMA

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

    # 3. RULE 1: UNCONDITIONAL PASS-THROUGH FOR CONTINUATION STATES
    if mkt_entry in ["BULL", "BEAR"]:
        final_signal = mkt_entry

    # 4. RULE 2: TREND ENGINE CROSSOVERS GO STRAIGHT TO OTM
    elif trend_entry == "BUY":
        final_signal = "OTMBUY"
    elif trend_entry == "SELL":
        final_signal = "OTMSELL"

    # 5. RULE 3: MARKET ENGINE SIGNAL CROSS-FILTRATION LAYER
    elif mkt_entry == "BUY":
        # Maps to OTM if trend is aligned, otherwise falls back to AVG
        final_signal = "OTMBUY" if trend_entry == "NORTH" else "AVGBUY"
        
    elif mkt_entry == "SELL":
        # Maps to OTM if trend is aligned, otherwise falls back to AVG
        final_signal = "OTMSELL" if trend_entry == "SOUTH" else "AVGSELL"

    # 6. SYSTEM STABILITY FALLBACK
    else:
        # Default tracking structure for quiet market intervals
        if trend_entry == "NORTH":
            final_signal = "AVGBUY"
        elif trend_entry == "SOUTH":
            final_signal = "AVGSELL"
        else:
            final_signal = "NONE"

    # Console Status Reporting Actions
    if final_signal != "NONE":
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




