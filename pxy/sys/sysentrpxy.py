# sysentrpxy.py
from sysmktpxy import get_signal
from syscnfgpxy import TICKER
from datetime import datetime
from zoneinfo import ZoneInfo

def get_entry_signal(df=None):
    # 1. Fetch Synced Signals from sysmktpxy
    # entry_l4: Contains "BUY", "SELL", "BULL", "BEAR", or "NONE"
    # exit_l2: Contains the P-Master exit signals
    entry_l4, exit_l2 = get_signal(df)

    # 2. ACTION MAPPING LOGIC
    # We only create ATM actions for the specific crossing/touch events.
    # Everything else passes through as the raw string.
    
    final_signal = "NONE"

    if entry_l4 == "BUY":
        final_signal = "ATMBUY"
    elif entry_l4 == "SELL":
        final_signal = "ATMSELL"
    else:
        # Pass BULL, BEAR, or NONE exactly as they are
        final_signal = entry_l4

    # Reporting only on Action Signals
    if final_signal in ["ATMBUY", "ATMSELL"]:
        print(f"🔥 ACTION TRIGGERED: {final_signal} 🔥".center(36))
    
    return final_signal, exit_l2

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 36)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")





