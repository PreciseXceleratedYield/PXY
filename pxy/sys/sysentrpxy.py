# pxy_routing_engine.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH SIMPLIFIED CO-ROUTING PIPELINES
===============================================================================
Operational Rules Matrix:
1. IST Morning 09:15 to 09:20: BOTH Entry & Exit driven by sysexitpxy.
2. After 09:20 IST          : BOTH Entry & Exit driven by sysmktpxy.
===============================================================================
"""

import pandas as pd
from syscnfgpxy import TICKER
from sysmktpxy import get_signal 
from sysexitpxy import detect_raw_direction

def get_entry_signal(df=None):
    """
    Dynamically routes option entry and structural exit signals together 
    based strictly on the IST candle clock window bounds.
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

    # 2. Determine if the current tick falls into the 09:15 - 09:20 IST window
    is_opening_window = (current_hour == 9 and 15 <= current_minute < 20)

    # 3. Dynamic Matrix Switch Execution Block
    if is_opening_window:
        # 09:15 to 09:20: BOTH entry and exit are driven entirely by sysexitpxy
        _, exit_dir = detect_raw_direction(df)
        
        # Route Entry
        if exit_dir == "UP":
            entry_signal = "ATMBUY"
            exit_signal = "BULL"
        elif exit_dir == "DOWN":
            entry_signal = "ATMSELL"
            exit_signal = "BEAR"
        else:
            entry_signal = "NONE"
            exit_signal = "NONE"
            
        routing_mode_text = "[MODE: MORNING VOLATILITY (PURE EXITPXY DRIVEN)]"
    else:
        # After 09:20: BOTH entry and exit are driven entirely by sysmktpxy
        mkt_dir, _ = get_signal(df)
        
        # Route Entry
        if mkt_dir == "BULL":
            entry_signal = "ATMBUY"
            exit_signal = "BULL"
        elif mkt_dir == "BEAR":
            entry_signal = "ATMSELL"
            exit_signal = "BEAR"
        else:
            entry_signal = "NONE"
            exit_signal = "NONE"
            
        routing_mode_text = "[MODE: NORMAL MARKET (PURE MKTPXY DRIVEN)]"

    # 4. Console Status Reporting Actions
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
