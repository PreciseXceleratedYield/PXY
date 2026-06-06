"""
===============================================================================
PXY OPTION ROUTING ENGINE: HIGH-VELOCITY STRUCTURAL BREAKOUT PRIORITY
===============================================================================
Operational Rules:
- EXIT signals originate strictly from sysmktpxy (exit_sig).
- ENTRY Layer A (👑 PRIORITY 1): Pure structural breakout from sysbbospxy (bos_signal).
  If a 42-minute high/low floor is broken, it takes immediate ATM placement.
- ENTRY Layer B (📈 PRIORITY 2): Trend Breakouts requiring strict 'and' harmony.
  Fires strictly when a fresh trigger AND the macro trend are in absolute agreement.
- NO OVERRIDES: Section 5 has been completely stripped out to enforce pure pipe logic.
===============================================================================
"""

import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from syscnfgpxy import TICKER

# Ingestion gateways from your exact strategy matrix modules
from sysmktpxy import get_signal, CHECK_CONFIRMED_ONLY
from sysstrndpxy import calculate_supertrend
from sysbbospxy import get_bos_bar  # Ingesting your 42-min structural breakout engine

def get_entry_signal(df=None):
    # 1. Extract EXIT signal strictly from Priority 1 Engine (sysmktpxy)
    _, exit_sig = get_signal(df)
    exit_sig = str(exit_sig).upper().strip()

    # 2. Extract ENTRY signals strictly from your upstream strategy files
    # --- LAYER A: Query sysbbospxy for immediate high-volume structural breakouts ---
    dummy_df = pd.DataFrame() if df is None else df.copy()
    _, bos_signal = get_bos_bar(dummy_df)
    bos_signal = str(bos_signal).upper().strip()

    # --- LAYER B: Query your upstream 10:3 Engine (sysstrndpxy) ---
    strnd_df = calculate_supertrend(df=None)
    
    strnd_signal = "NONE"
    strnd_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        try:
            # Extract both metrics simultaneously from database columns
            strnd_signal = str(strnd_df.iloc[idx]['st_signal_full']).upper().strip()
            strnd_trend  = str(strnd_df.iloc[idx]['st_trend_full']).upper().strip()
        except Exception:
            pass

    # 3. Establish Base Current Time in Indian Standard Time (IST)
    tz_ist = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(tz_ist).time()

    if strnd_df is not None and not strnd_df.empty:
        try:
            last_timestamp = strnd_df.index[-1]
            if not isinstance(last_timestamp, pd.Timestamp):
                last_timestamp = pd.to_datetime(last_timestamp)
            current_time_ist = last_timestamp.astimezone(tz_ist).time() if last_timestamp.tzinfo is not None else last_timestamp.time()
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
        # --- STANDARD CONTINUOUS WINDOW: DECISIVE PRIORITY PLACEMENT CORE ---
        
        # 👑 👑 👑 PRIORITY 1: High-Volume 42-Min Structural Breakouts (sysbbospxy) OVERRULE
        if bos_signal == "BUY":
            final_signal = "ATMBUY"
        elif bos_signal == "SELL":
            final_signal = "ATMSELL"
            
        # 📈 PRIORITY 2: Direct Upstream-Filtered Action Gates 
        # Evaluates strict point-in-time trigger AND master macro trend
        elif strnd_signal == "BUY" and strnd_trend == "BULL":
            final_signal = "ATMBUY"
        elif strnd_signal == "SELL" and strnd_trend == "BEAR":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"

    # 6. OPTIMIZED TELEMETRY ALERT ENGINE
    if final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    return final_signal, exit_sig

if __name__ == "__main__":
    print("\n[PXY ROUTER STATUS] Upstream Filtered Option Route Matrix Active.")
    print("-" * 50)
    final_route, raw_exit = get_entry_signal(df=None)
    print("-" * 50)
    print(f"FINAL DECISION >> ROUTE STATUS: {final_route} | RAW EXIT FROM MKT: {raw_exit}")
