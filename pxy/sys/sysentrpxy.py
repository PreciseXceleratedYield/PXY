"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH DECENTRALIZED MULTI-PIPELINE INTEGRATION
===============================================================================
Timezone Configuration: Aligned strictly to Indian Standard Time (IST) Zone.

Operational Rules Matrix (Indian Markets):
1. Window [09:15 IST - 09:30 IST]: Routes raw sysmktpxy candle momentum flips.
   - exit_sig == "BUY"  -> ATMBUY
   - exit_sig == "SELL" -> ATMSELL
2. Window [After 09:30 IST]: Kick-starts priority routing filters.
   - PRIORITY 1 OVERRULE (sysmktpxy Definitives):
     * If mkt_entry == "BUY"  -> ATMBUY (Immediate Action)
     * If mkt_entry == "SELL" -> ATMSELL (Immediate Action)
   - PRIORITY 2 MULTI-PIPELINE (sysemixpxy Leading Price Action):
     * Condition: If sysmktpxy is in a 'BULL' or 'BEAR' passive trend state
     * Action: Queries sysemixpxy.py leading pipelines for explosive entries.
===============================================================================
"""

import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from syscnfgpxy import TICKER

# Ingestion gateways from your verified architectural module matrix
from sysmktpxy import get_signal, CHECK_CONFIRMED_ONLY
from sysemixpxy import get_live_matrix_signal

def get_entry_signal(df=None):
    # 1. Fetch the raw, unfiltered structural state maps from Master Priority 1 (sysmktpxy)
    mkt_entry, exit_sig = get_signal(df)

    # Clean and standardize incoming string formats to avoid whitespace anomalies
    mkt_entry = str(mkt_entry).upper().strip()
    exit_sig  = str(exit_sig).upper().strip()

    # 2. Establish Base Current Time in Indian Standard Time (IST)
    tz_ist = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(tz_ist).time()

    # Parse dataframe time if present to ensure proper sync with live index data
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

    market_open = datetime.strptime("09:15", "%H:%M").time()
    time_boundary = datetime.strptime("09:30", "%H:%M").time()

    final_signal = "NONE"
    
    # Code continues smoothly into Part 2...
    # 3. IST TIME-BASED OPTIONS ROUTING ENGINE
    if market_open <= current_time_ist < time_boundary:
        # --- EARLY MORNING OPENING WINDOW: PURE RAW REVERSAL TO ATM ---
        if exit_sig == "BUY":
            final_signal = "ATMBUY"
        elif exit_sig == "SELL":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"
    else:
        # --- STANDARD CONTINUOUS WINDOW: DECISIVE PRIORITY FILTER CORE ---
        
        # 👑 PRIORITY 1: sysmktpxy Definitive Breakout Triggers take immediate ATM placement
        if mkt_entry == "BUY":
            final_signal = "ATMBUY"
        elif mkt_entry == "SELL":
            final_signal = "ATMSELL"
            
        # ⚡ PRIORITY 2: sysmktpxy Trend Holds (BULL/BEAR) pass routing authority to sysemixpxy leading pipelines
        elif mkt_entry in ["BULL", "BEAR"]:
            # Query your 13 decentralized price action pipelines for an immediate trigger
            emix_signal = get_live_matrix_signal()
            emix_signal = str(emix_signal).upper().strip()
            
            if emix_signal == "BUY":
                final_signal = "ATMBUY"
            elif emix_signal == "SELL":
                final_signal = "ATMSELL"
            else:
                final_signal = mkt_entry  # Keep the passive BULL/BEAR trend state if no pipeline hits
                
        else:
            # Pass remaining native states down the line (NONE)
            final_signal = mkt_entry

    # 4. LATE OVERRIDE FALLBACK (Strictly for downstream communication pass-through)
    if final_signal in ["NONE", "BULL", "BEAR"]:
        if exit_sig == "BUY":
            final_signal = "BUY"
        elif exit_sig == "SELL":
            final_signal = "SELL"
        else:
            final_signal = exit_sig  # Safely passes remaining trend metrics downstream

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


