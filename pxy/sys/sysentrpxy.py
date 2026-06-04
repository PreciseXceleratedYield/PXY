# sysentrpxy.py
"""
===============================================================================
PXY EXECUTION OPTION ROUTING ENGINE WITH IST TIME-WINDOW CONTROLS
===============================================================================
Timezone Configuration: Aligned strictly to Indian Standard Time (IST) Zone.

Operational Rules Matrix (Indian Markets):
1. Window [09:15 IST - 09:30 IST]: Bypasses entry core. Routes raw candle flips.
   - exit_sig == "BUY"  -> ATMBUY
   - exit_sig == "SELL" -> ATMSELL
2. Window [After 09:30 IST]: Kick-starts priority routing filters.
   - CROSS OVERRULE (PRIORITY 1): 
     * True HA Crossover Above Baseline -> ATMBUY (Immediate Action)
     * True HA Crossover Below Baseline -> ATMSELL (Immediate Action)
   - TREND FILTERS (PRIORITY 2):
     * If Trend is Bullish and exit_sig == "BUY"  -> ATMBUY (Trend Pullback)
     * If Trend is Bearish and exit_sig == "SELL" -> ATMSELL (Trend Pullback)
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
    # 1. Fetch the raw, unfiltered Heikin-Ashi candle state maps
    mkt_entry, exit_sig = get_signal(df)

    # 2. Extract the underlying 380 baseline macro trend and crossover signals
    # We pass df=None to let it utilize its internal yFinance multi-day cache
    strnd_df = calculate_supertrend(df=None)
    
    macro_trend = "NEUTRAL"
    has_cross_buy = False
    has_cross_sell = False

    if strnd_df is not None and not strnd_df.empty:
        # Align lookup index to match your switch state (Confirmed vs Live Running)
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        
        try:
            macro_trend = str(strnd_df.iloc[idx]['st_trend_full']).upper().strip()
            
            # Identify the explicit structural trend cross event state markers
            cross_event = str(strnd_df.iloc[idx]['st_signal_full']).upper().strip()
            has_cross_buy = (cross_event == "CROSSBUY")
            has_cross_sell = (cross_event == "CROSSSELL")
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

    market_open = datetime.strptime("09:15", "%H:%M").time()
    time_boundary = datetime.strptime("09:30", "%H:%M").time()

    final_signal = "NONE"

    # 4. IST TIME-BASED OPTIONS ROUTING ENGINE
    if market_open <= current_time_ist < time_boundary:
        # --- EARLY MORNING OPENING WINDOW: PURE RAW REVERSAL TO ATM ---
        if exit_sig == "BUY":
            final_signal = "ATMBUY"
        elif exit_sig == "SELL":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"
    else:
        # --- STANDARD CONTINUOUS WINDOW: PRIORITY EXECUTION CORE ---
        
        # 👑 PRIORITY 1: Crossover Breakouts take immediate ATM placement
        if has_cross_buy:
            final_signal = "ATMBUY"
        elif has_cross_sell:
            final_signal = "ATMSELL"
            
        # 📈 PRIORITY 2: Trend Filter Pullbacks (Trend is BULL + Heikin-Ashi flips Green)
        elif macro_trend == "BULL" and exit_sig == "BUY":
            final_signal = "ATMBUY"
            
        # 📉 PRIORITY 3: Trend Filter Pullbacks (Trend is BEAR + Heikin-Ashi flips Red)
        elif macro_trend == "BEAR" and exit_sig == "SELL":
            final_signal = "ATMSELL"
            
        else:
            # Pass remaining native states down the line
            final_signal = mkt_entry

    # 5. LATE OVERRIDE FALLBACK (Strictly for downstream communication pass-through)
    if final_signal in ["NONE", "BULL", "BEAR"]:
        if exit_sig == "BUY":
            final_signal = "BUY"
        elif exit_sig == "SELL":
            final_signal = "SELL"
        else:
            final_signal = exit_sig  # Safely passes BULL, BEAR, or NONE downstream

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



