# pxy_routing_engine.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH TIME-CONDITIONAL PIPELINES
===============================================================================
Operational Rules Matrix:
1. IST Morning 09:15 to 09:20: ENTRY is driven by sysexitpxy (for fast ATM execution).
2. After 09:20 IST          : ENTRY is driven by sysmktpxy.
3. EXIT Pipeline            : Always driven independently by sysexitpxy.
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal 
from sysexitpxy import detect_raw_direction

def get_entry_signal(df=None):
    """
    Dynamically routes option signals based on the IST candle clock.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Extract the exact IST time components from the latest candle timestamp
    latest_timestamp = df.index[-1]
    current_hour = latest_timestamp.hour
    current_minute = latest_timestamp.minute

    # 2. Query both independent calculation modules
    mkt_dir, _ = get_signal(df)
    _, exit_dir = detect_raw_direction(df)

    # 3. Determine if the current tick falls into the 09:15 - 09:20 IST window
    is_opening_window = (current_hour == 9 and 15 <= current_minute < 20)

    # 4. Route ENTRY signal based on time block rule
    if is_opening_window:
        # 09:15 to 09:20 morning window: use exit signal direction for ATM entries
        if exit_dir == "UP":
            entry_signal = "ATMBUY"
        elif exit_dir == "DOWN":
            entry_signal = "ATMSELL"
        else:
            entry_signal = "NONE"
        routing_mode_text = "[MODE: OPENING VOLATILITY (EXIT DRIVEN)]"
    else:
        # After 09:20: use standard market engine direction
        if mkt_dir == "BULL":
            entry_signal = "ATMBUY"
        elif mkt_dir == "BEAR":
            entry_signal = "ATMSELL"
        else:
            entry_signal = "NONE"
        routing_mode_text = "[MODE: NORMAL MARKET (MKTPXY DRIVEN)]"

    # 5. Route EXIT signal (always driven by sysexitpxy)
    if exit_dir == "UP":
        exit_signal = "BULL"
    elif exit_dir == "DOWN":
        exit_signal = "BEAR"
    else:
        exit_signal = "NONE"

    # Console Status Reporting Actions
    print(f"🕒 Time: {latest_timestamp.strftime('%H:%M')} IST | {routing_mode_text}")
    if entry_signal != "NONE" or exit_signal != "NONE":
        print(f"      🔥 [ACTION] -> ENTRY: {entry_signal} | EXIT: {exit_signal} 🔥")
    else:
        print("💤 [STANDBY] -> Market Flat Line Detected. Action Terminated. 💤")

    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")

