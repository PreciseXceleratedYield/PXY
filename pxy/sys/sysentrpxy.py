# sysoptionrtpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX & REGIME PRIORITY
===============================================================================
Operational Rules Matrix:
1. EXIT Pipeline  : Unconditionally mapped to get_signal (UP -> BULL | DOWN -> BEAR).
2. ENTRY Pipeline : Filtered by strict, mutually exclusive structural regimes.
===============================================================================
"""

# Import the signal functions from your engines
from sysmktpxy import get_signal      # Direction engine (UP / DOWN)
from sysstrndpxy import calculate_supertrend  # Structural engine (BULL / BEAR)
from syscnfgpxy import TIMEZONE, TICKER
import pandas as pd
from datetime import datetime
import pytz

def get_entry_signal(df=None):
    """
    Advanced routing pipeline mapping structural trend regimes against execution signals.
    Exits follow live direction unconditionally. All conditions run on 100% 
    isolated exclusive tracks with zero nested fallback layers or loops.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Extract the geometric movement direction (UP / DOWN)
    direction, _ = get_signal(df)

    # 2. Extract the true SuperTrend regime matrix state (BULL / BEAR)
    processed_df = calculate_supertrend(df)
    current_regime = str(processed_df['sma_trend_full'].iloc[-1]) # Last row state

    # =========================================================================
    # INTRADAY TIMING FILTER LAYER (IST Market Clock Tracking)
    # =========================================================================
    last_timestamp = processed_df.index[-1]
    
    # Enforce correct IST timezone conversion for rule checking
    ist_tz = pytz.timezone('Asia/Kolkata')
    if last_timestamp.tzinfo is None:
        last_timestamp = last_timestamp.localize(pytz.utc).astimezone(ist_tz)
    else:
        last_timestamp = last_timestamp.astimezone(ist_tz)
        
    current_hour = last_timestamp.hour
    current_minute = last_timestamp.minute
    
    # Mathematical time translation to check if inside 09:15 IST to 09:30 IST window
    time_in_minutes = (current_hour * 60) + current_minute
    start_window_minutes = (9 * 60) + 15  # 09:15
    end_window_minutes = (9 * 60) + 30    # 09:30
    
    is_morning_otm_window = (time_in_minutes >= start_window_minutes) and (time_in_minutes <= end_window_minutes)

    entry_signal = "NONE"
    
    # =========================================================================
    # UNCONDITIONAL EXIT MAPPING (Restored to your original engine rules)
    # =========================================================================
    exit_signal = "BULL" if direction == "UP" else "BEAR"

    # =========================================================================
    # ENTRY FILTER MATRIX & PRIORITY LAYER (Strictly Exclusive & Flattened)
    # =========================================================================
    
    # --- 1. MORNING SESSION CODES (09:15 - 09:30 IST) ---
    is_morning_buy_trigger  = (is_morning_otm_window) and (current_regime == "BULL") and (direction == "UP")
    is_morning_sell_trigger = (is_morning_otm_window) and (current_regime == "BEAR") and (direction == "DOWN")
    
    # --- 2. STANDARD SESSION CODES (09:31 IST ONWARDS) ---
    is_standard_buy_trigger  = (not is_morning_otm_window) and (current_regime == "BULL") and (direction == "UP")
    is_standard_sell_trigger = (not is_morning_otm_window) and (current_regime == "BEAR") and (direction == "DOWN")
    
    # --- 3. TIME-AGNOSTIC PROTECTIVE CODES ---
    is_bull_hedge_trigger = (current_regime == "BULL") and (direction == "DOWN")
    is_bear_hedge_trigger = (current_regime == "BEAR") and (direction == "UP")

    # --- 4. EXCLUSIVE SIGNAL DIRECT ASSIGNMENT RUNTIME (No Elif, No Else) ---
    if is_morning_buy_trigger:
        entry_signal = "OTMBUY"
        
    if is_morning_sell_trigger:
        entry_signal = "OTMSELL"
        
    if is_standard_buy_trigger:
        entry_signal = "ATMBUY"
        
    if is_standard_sell_trigger:
        entry_signal = "ATMSELL"
        
    if is_bull_hedge_trigger:
        entry_signal = "BEAR"
        
    if is_bear_hedge_trigger:
        entry_signal = "BULL"

    # =========================================================================
    # KEEPING PRINT LINES EXACTLY LIKE ORIGINAL CODE
    # =========================================================================
    if entry_signal != "NONE":
        print(f"          SUPER: {current_regime} | MOVE: {direction}")
        print(f"          ENTRY: {entry_signal} | EXIT: {exit_signal}")

    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL PROCESSED EXECUTION >> ENTRY: {entry} | EXIT: {ex}")
