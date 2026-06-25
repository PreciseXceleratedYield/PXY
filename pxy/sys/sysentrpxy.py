"""
# sysentrpxy.py
===============================================================================
PXY EXECUTION OPTION ROUTING ENGINE WITH IST TIME-WINDOW CONTROLS
===============================================================================
Timezone Configuration: Aligned strictly to Indian Standard Time (IST) Zone.

Operational Rules Matrix (Indian Markets):
1. Window [09:15 IST - 09:30 IST]: Bypasses entry core. Routes raw exit_l2 to ATM.
   - exit_l2 == "BUY" or "NORTH" -> ATMBUY
   - exit_l2 == "SELL" or "SOUTH" -> ATMSELL
2. Window [After 09:30 IST]: Strict Entry Core Filtering.
   - ALL Trend-Aligned & Crossovers (BUY, SELL, NORTH, SOUTH) -> ATMBUY / ATMSELL
   - Any non-aligned or ambiguous states -> AVGBUY / AVGSELL fallback
3. Fallback Route: Preserves structural reporting states downstream.
===============================================================================
"""

from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

def get_entry_signal(df=None):
    # 1. Fetch Synced Signals from sysmktpxy (Mapped from sysstrndpxy)
    # entry_l4 maps to entry_signal (index -2), exit_l2 maps to exit_signal (index -1)
    entry_l4, exit_l2 = get_signal(df)

    # 2. Establish Base Current Time in Indian Standard Time (IST)
    tz_ist = ZoneInfo("Asia/Kolkata")
    current_time_ist = datetime.now(tz_ist).time()

    # Parse dataframe time if present to ensure proper sync with tracking data
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

    # Create explicit time objects for IST boundary matching
    market_open = datetime.strptime("09:15", "%H:%M").time()
    time_boundary = datetime.strptime("09:30", "%H:%M").time()

    final_signal = "NONE"

    # 3. IST TIME-BASED OPTIONS ROUTING ENGINE
    if market_open <= current_time_ist < time_boundary:
        # --- EARLY MORNING OPENING WINDOW: ALL ACTIVE MOTIONS ROUTE TO ATM ---
        if exit_l2 in ["BUY", "NORTH"]:
            final_signal = "ATMBUY"
        elif exit_l2 in ["SELL", "SOUTH"]:
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"
    else:
        # --- STANDARD CONTINUOUS WINDOW: TREND-ALIGNED & CROSSOVER PASS TO ATM ---
        if entry_l4 in ["BUY", "NORTH"]:
            final_signal = "ATMBUY"
        elif entry_l4 in ["SELL", "SOUTH"]:
            final_signal = "ATMSELL"
        else:
            # --- DEFENSIVE FALLBACK LAYER: UNALIGNED STATES RESOLVE TO AVG ---
            if exit_l2 in ["BUY", "NORTH"]:
                final_signal = "AVGBUY"
            elif exit_l2 in ["SELL", "SOUTH"]:
                final_signal = "AVGSELL"
            else:
                final_signal = "AVGSELL" # Safe system default for structural compliance

    # 4. LATE OVERRIDE FALLBACK (Strictly for downstream communication pass-through)
    if final_signal == "NONE":
        if exit_l2 in ["BUY", "NORTH"]:
            final_signal = "BUY"
        elif exit_l2 in ["SELL", "SOUTH"]:
            final_signal = "SELL"
        else:
            final_signal = exit_l2  # Safely passes remaining codes downstream

    # Reporting on active Indian Market signals
    if final_signal in ["ATMBUY", "ATMSELL", "AVGBUY", "AVGSELL", "BUY", "SELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")

