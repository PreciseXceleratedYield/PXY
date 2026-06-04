# sysentrpxy.py
"""
===============================================================================
PXY EXECUTION OPTION ROUTING ENGINE WITH IST TIME-WINDOW CONTROLS
===============================================================================
Timezone Configuration: Aligned strictly to Indian Standard Time (IST) Zone.

Operational Rules Matrix (Indian Markets):
1. Window [09:15 IST - 09:30 IST]: Bypasses entry core. Routes raw candle flips to OTM.
   - exit_sig == "BUY"  -> OTMBUY
   - exit_sig == "SELL" -> OTMSELL
2. Window [After 09:30 IST]: Kick-starts priority routing filters.
   - CROSS OVERRULE (PRIORITY 1) - Hierarchical Structure:
     * Rank 1: Band Wick Touches -> BB (ATMBUY) / BS (ATMSELL)
     * Rank 2: Mid-Line Crosses  -> MB (ATMBUY) / MS (ATMSELL)
     * Rank 3: 15m HA Line Cross -> CB (ATMBUY) / CS (ATMSELL)
   - TREND FILTER FOLLOWERS (PRIORITY 2):
     * If Trend is Bullish and exit_sig == "BUY"  -> ATMBUY (Trend Pullback)
     * If Trend is Bearish and exit_sig == "SELL" -> ATMSELL (Trend Pullback)
   - OPPOSITE MEAN REVERSION FLIPS (PRIORITY 3):
     * If Trend is Bullish and exit_sig == "SELL" -> OTMSELL (Counter-Trend Short)
     * If Trend is Bearish and exit_sig == "BUY"  -> OTMBUY (Counter-Trend Long)
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

    market_open = datetime.strptime("09:15", "%H:%M").time()
    time_boundary = datetime.strptime("09:30", "%H:%M").time()

    final_signal = "NONE"

    # 4. IST TIME-BASED OPTIONS ROUTING ENGINE
    if market_open <= current_time_ist < time_boundary:
        # --- EARLY MORNING OPENING WINDOW: PURE RAW REVERSAL TO OTM ---
        if exit_sig == "BUY":
            final_signal = "OTMBUY"
        elif exit_sig == "SELL":
            final_signal = "OTMSELL"
        else:
            final_signal = "NONE"
    else:
        # --- STANDARD CONTINUOUS WINDOW: PRIORITY EXECUTION CORE ---
        
        # 👑 PRIORITY 1: Hierarchical Breakout Evaluation Matrix
        # Rank 1: Volatility Outer Band Wick Touches
        if "BB" in cross_event:
            final_signal = "ATMBUY"
        elif "BS" in cross_event:
            final_signal = "ATMSELL"
            
        # Rank 2: Middle TSMA Line Crossovers
        elif "MB" in cross_event:
            final_signal = "ATMBUY"
        elif "MS" in cross_event:
            final_signal = "ATMSELL"
            
        # Rank 3: Macro 15m Heikin Ashi Open Baseline Crossings
        elif "CB" in cross_event:
            final_signal = "ATMBUY"
        elif "CS" in cross_event:
            final_signal = "ATMSELL"
            
        # 📈 PRIORITY 2: Trend Filter Pullbacks (Aligned with Trend)
        elif macro_trend == "BULL" and exit_sig == "BUY":
            final_signal = "ATMBUY"
        elif macro_trend == "BEAR" and exit_sig == "SELL":
            final_signal = "ATMSELL"
            
        # 🛡️ PRIORITY 3: Opposite Market Flips (Counter-Trend Mean Reversion to OTM)
        elif macro_trend == "BULL" and exit_sig == "SELL":
            final_signal = "OTMSELL"
        elif macro_trend == "BEAR" and exit_sig == "BUY":
            final_signal = "OTMBUY"
            
        else:
            # Pass remaining native states down the line (BULL, BEAR, or NONE)
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
    if final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL", "BUY", "SELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    return final_signal, exit_sig

if __name__ == "__main__":
    print("\n[PXY ROUTER STATUS] Option Route Verification Matrix Active.")
    print("-" * 50)
    final_route, raw_exit = get_entry_signal(df=None)
    print("-" * 50)
    print(f"FINAL DECISION >> ROUTE STATUS: {final_route} | RAW CANDLE FLIP: {raw_exit}")
