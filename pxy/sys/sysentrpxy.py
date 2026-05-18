# sysentrpxy.py
"""
===============================================================================
PXY EXECUTION OPTION ROUTING ENGINE WITH IST TIME-WINDOW CONTROLS
===============================================================================
Timezone Configuration: Aligned strictly to Indian Standard Time (IST) Zone.

Operational Rules Matrix (Indian Markets):
1. Window [09:15 IST - 09:30 IST]: Bypasses entry core. Routes raw exit_l2.
   - exit_l2 == "BUY"  -> ATMBUY
   - exit_l2 == "SELL" -> ATMSELL
2. Window [After 09:30 IST]: Kick-starts standard entry_l4 structural filters.
   - CROSSBUY / CROSSSELL -> OTMBUY / OTMSELL
   - TRENDBUY / TRENDSELL -> ATMBUY / ATMSELL
3. Fallback Route: If final_signal resolves to "NONE", it extracts the clean
   raw exit_l2 state to pass straight down to the downstream process.
===============================================================================
"""

from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

def get_entry_signal(df=None):
    # 1. Fetch Synced Signals from sysmktpxy
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
        # --- EARLY MORNING OPENING WINDOW: PURE RAW REVERSAL TO ATM ---
        if exit_l2 == "BUY":
            final_signal = "OTMBUY"
        elif exit_l2 == "SELL":
            final_signal = "OTMSELL"
        else:
            final_signal = "NONE"
    else:
        # --- STANDARD CONTINUOUS WINDOW: ACTIVE ENTRY FILTER CORE ---
        if entry_l4 == "CROSSBUY":
            final_signal = "OTMBUY"
        elif entry_l4 == "CROSSSELL":
            final_signal = "OTMSELL"
        elif entry_l4 == "TRENDBUY":
            final_signal = "ATMBUY"
        elif entry_l4 == "TRENDSELL":
            final_signal = "ATMSELL"
        elif entry_l4 == "FLIPSELL":
            final_signal = "OTMSELL"
        elif entry_l4 == "FLIPBUY":
            final_signal = "OTMBUY"
        elif entry_l4 == "FLOWSELL":
            final_signal = "OTMSELL"
        elif entry_l4 == "FLOWBUY":
            final_signal = "OTMBUY"           
        else:
            # Pass BULL, BEAR, or NONE exactly as they are down the line
            final_signal = entry_l4


    # 4. LATE OVERRIDE FALLBACK (Strictly for downstream communication pass-through)
    if final_signal == "NONE":
        if exit_l2 == "BUY":
            final_signal = "BUY"
        elif exit_l2 == "SELL":
            final_signal = "SELL"
        else:
            final_signal = exit_l2  # Safely passes BULL, BEAR, or NONE downstream

    # Reporting on active Indian Market signals
    if final_signal in ["OTMBUY", "OTMSELL", "ATMBUY", "ATMSELL", "BUY", "SELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")






