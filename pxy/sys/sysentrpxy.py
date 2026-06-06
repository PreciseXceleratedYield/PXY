"""
===============================================================================
PXY OPTION ROUTING ENGINE: DIRECT UPSTREAM-FILTERED CORE
===============================================================================
Operational Rules:
- EXIT signals originate strictly from sysmktpxy (exit_sig).
- ENTRY signals originate strictly from your pre-filtered sysstrndpxy.py engine.
- ZERO RE-CHECKING: Bypasses redundant trend checks since filtering happens upstream.
- STRICT LOGGING: Console alerts fire ONLY for active options contract placements.
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
    # 1. Extract EXIT signal strictly from Priority 1 Engine (sysmktpxy)
    _, exit_sig = get_signal(df)
    exit_sig = str(exit_sig).upper().strip()

    # 2. Extract ENTRY signals strictly from your upstream 10:3 Engine (sysstrndpxy)
    strnd_df = calculate_supertrend(df=None)
    strnd_signal = "NONE"

    if strnd_df is not None and not strnd_df.empty:
        idx = -2 if CHECK_CONFIRMED_ONLY else -1
        try:
            # Captures the full unfiltered signal array ('BUY', 'SELL', 'BULL', 'BEAR', or 'NONE')
            strnd_signal = str(strnd_df.iloc[idx]['st_signal_full']).upper().strip()
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
        # --- STANDARD CONTINUOUS WINDOW: MULTI-STATE OPTIONS PLACEMENT ---
        # Fixed logic gate: Evaluates both trigger events and running trend strings cleanly
        if strnd_signal == "BUY" or strnd_signal == "BULL":
            final_signal = "ATMBUY"
        elif strnd_signal == "SELL" or strnd_signal == "BEAR":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"

    # 5. LATE OVERRIDE FALLBACK (Downstream pass-through safety handler)
    if final_signal in ["NONE", "BULL", "BEAR"]:
        if exit_sig == "BUY":
            final_signal = "BUY"
        elif exit_sig == "SELL":
            final_signal = "SELL"
        else:
            final_signal = exit_sig

    # 6. OPTIMIZED TELEMETRY ALERT ENGINE
    # Completely ignores standard text strings. Fires ONLY for actionable option contracts.
    if final_signal in ["ATMBUY", "ATMSELL", "OTMBUY", "OTMSELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    return final_signal, exit_sig

if __name__ == "__main__":
    print("\n[PXY ROUTER STATUS] Upstream Filtered Option Route Matrix Active.")
    print("-" * 50)
    final_route, raw_exit = get_entry_signal(df=None)
    print("-" * 50)
    print(f"FINAL DECISION >> ROUTE STATUS: {final_route} | RAW EXIT FROM MKT: {raw_exit}")
