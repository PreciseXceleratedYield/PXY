# sysentrpxy.py
from sysmktpxy import get_signal  # <-- Import from Tier 2 Network Layer
try:
    from syscnfgpxy import TICKER
except ImportError:
    TICKER = "NSE_INDEX"
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

def get_entry_signal(df=None):
    # 1. Fetch Synced Signals from Tier 2 Interface Layer
    entry_l4, exit_l2 = get_signal(df)

    # 2. Establish Base Current Time in Indian Standard Time (IST)
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

    market_open = datetime.strptime("09:15", "%H:%M").time()
    time_boundary = datetime.strptime("09:30", "%H:%M").time()
    final_signal = "NONE"

    # 3. IST TIME-BASED OPTIONS ROUTING ENGINE (ALL ATM EXECUTION CHANNELS)
    if market_open <= current_time_ist < time_boundary:
        if exit_l2 == "BUY":
            final_signal = "ATMBUY"
        elif exit_l2 == "SELL":
            final_signal = "ATMSELL"
        else:
            final_signal = "NONE"
    else:
        if entry_l4 == "BUY":
            final_signal = "ATMBUY"
        elif entry_l4 == "SELL":
            final_signal = "ATMSELL"
        else:
            final_signal = entry_l4

    # 4. OVERRIDE FALLBACK PASS-THROUGH HANDLERS
    if final_signal == "NONE":
        if exit_l2 == "BUY":
            final_signal = "BUY"
        elif exit_l2 == "SELL":
            final_signal = "SELL"
        else:
            final_signal = exit_l2  

    if final_signal in ["ATMBUY", "ATMSELL", "BUY", "SELL"]:
        print(f"⏰ [IST: {current_time_ist.strftime('%H:%M:%S')}] 🔥 ACTION-{final_signal} 🔥 ".center(40))

    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    print("\n=== [TIER 3] Execution Pipeline Final Self-Test ===")
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT TRANSACTION TRIPPED >> ENTRY ROUTE: {entry} | EXIT TRND: {ex}")


