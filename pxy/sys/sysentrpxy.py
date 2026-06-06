"""
===============================================================================
PXY OPTION ROUTING ENGINE: HIGH-VELOCITY UPSTREAM-FILTERED ENGINE (REPAIRED)
===============================================================================
Operational Rules:
- EXIT signals originate strictly from sysmktpxy (exit_sig).
- ENTRY Layer A (👑 PRIORITY 1): Pure structural breakout from sysbbospxy (bos_signal).
- ENTRY Layer B (📈 PRIORITY 2): Trend-following option contract assignment.
  Converts BOTH fresh breakout triggers and established trend states to trades.
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
    """
    Master Router. Extracts metrics from a single continuous historical data layer
    to completely prevent index mismatches and lookback starvation crashes.
    """
    # 1. DATA SYNCHRONIZATION AND MULTI-INDEX HEADER FLATTENING
    # If no data frame is passed from the master scheduler loop, seed an active container
    if df is None or df.empty:
        import yfinance as yf
        ticker_obj = yf.Ticker(TICKER)
        df = ticker_obj.history(period="5d", interval="1m")
        
    if df.empty:
        return "NONE", "NONE"
        
    master_df = df.copy()
    
    # Clean up multi-index column structures safely to avoid quiet KeyError failures
    if isinstance(master_df.columns, pd.MultiIndex):
        master_df.columns = master_df.columns.get_level_values(0)

    # 2. SEGREGATED INGESTION FLOW VIA INDEPENDENT PIPES
    # Extract EXIT signal strictly from Priority 1 Engine (sysmktpxy)
    _, exit_sig = get_signal(master_df)
    exit_sig = str(exit_sig).upper().strip()

    # Extract ENTRY Layer A: Pure 42-minute high/low structural breakouts
    _, bos_signal = get_bos_bar(master_df)
    bos_signal = str(bos_signal).upper().strip()

    # Extract ENTRY Layer B: Native 10:3 trailing band vectors
    strnd_df = calculate_supertrend(master_df)
    
    strnd_signal = "NONE"
    strnd_trend = "NEUTRAL"

    if strnd_df is not None and not strnd_df.empty:
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        try:
            # Successfully extracting BOTH metrics simultaneously from synchronized arrays
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
        # ✅ FIXED: Corrected syntax colons to ensure pristine Python compilation
        elif strnd_signal == "BUY" and strnd_trend == "BULL":
            final_signal = "ATMBUY"
        elif strnd_signal == "SELL" and strnd_trend == "BEAR":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"

    # 5. OPTIMIZED TELEMETRY ALERT ENGINE
    if final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    return final_signal, exit_sig

if __name__ == "__main__":
    print("\n[PXY ROUTER STATUS] Upstream Filtered Option Route Matrix Active.")
    print("-" * 50)
    final_route, raw_exit = get_entry_signal(df=None)
    print("-" * 50)
    print(f"FINAL DECISION >> ROUTE STATUS: {final_route} | RAW EXIT FROM MKT: {raw_exit}")

