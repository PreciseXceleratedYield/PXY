"""
===============================================================================
     PXY OPTION ROUTING ENGINE WITH TIME-BASED INTRA-DAY STRATEGY SHIFT
===============================================================================
Operational Rules Matrix:
1. ENTRY Pipeline: Converted cleanly into option targets based on time matrix.
   - BETWEEN 09:15 AND 10:15 IST -> Uses OTM Options (OTMBUY / OTMSELL)
   - ANY OTHER TIME              -> Uses ATM Options (ATMBUY / ATMSELL)
2. EXIT Pipeline : Returns the raw structural engine profile (BULL / BEAR / NONE).
===============================================================================
"""
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from syscnfgpxy import TICKER          # Direct streaming source connection
from sysmktpxy import get_signal       # Core geometric signal generation
from sysdthapxy import fetch_yf_data   # Standardized data fetching module

def is_otm_time_window():
    """
    Checks if current Indian Standard Time (IST) falls within 09:15 to 10:15.
    """
    # 1. Enforce localized timestamp mapping regardless of host machine timezone
    ist_tz = ZoneInfo("Asia/Kolkata")
    now_ist = datetime.now(ist_tz)
    
    # 2. Extract operational components
    current_time = now_ist.time()
    start_window = datetime.strptime("09:15", "%H:%M").time()
    end_window = datetime.strptime("10:15", "%H:%M").time()
    
    # 3. Evaluate boolean state
    return start_window <= current_time <= end_window

def get_entry_signal(df=None):
    """
    Direct routing pipeline mapping live exclusive raw signals from sysmktpxy.
    Injects dynamic OTM/ATM strike layer selection according to time windows.
    """
    # 1. Safe Fallback and Integrity Check
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        print("⚠️ [CRITICAL] Data payload empty. Engine entering safety standby.")
        return "NONE", "NONE"

    # 2. Determine Strike Target Selection (ATM vs OTM)
    strike_prefix = "OTM" if is_otm_time_window() else "ATM"

    # 3. Extract and Normalize Raw State Signals
    direction, _ = get_signal(df)
    direction_normalized = str(direction).strip().upper()

    # 4. Defensive Router Matrix Matching
    if direction_normalized == "BULL":
        entry_signal = f"{strike_prefix}BUY"
        exit_signal = "BULL"
    elif direction_normalized == "BEAR":
        entry_signal = f"{strike_prefix}SELL"
        exit_signal = "BEAR"
    else:
        entry_signal, exit_signal = "NONE", "NONE"

    # 5. Deterministic Console Reporting
    if entry_signal != "NONE":
        print(f" 🔥 [ACTION] -> {entry_signal} | {exit_signal} 🔥")
    else:
        print("💤 [STANDBY] -> Market Flat Line / Invalid State. Action Terminated. 💤")

    return entry_signal, exit_signal

if __name__ == "__main__":
    live_df = fetch_yf_data()
    entry, ex = get_entry_signal(live_df)
    print("-" * 50)
    print(f"FINAL RESULT >> ENTRY: {entry} | EXIT: {ex}")


