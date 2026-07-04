# sysoptionrtpxy.py
"""
===============================================================================
PXY OPTION ROUTING ENGINE WITH STREAMLINED CROSSOVER MATRIX & REGIME PRIORITY
===============================================================================
Operational Rules Matrix:
1. EXIT Pipeline  : Unconditionally mapped to get_signal (UP -> BULL | DOWN -> BEAR).
2. ENTRY Pipeline : Filtered by SuperTrend crossover and continuation regimes.
                    SIDE state bypasses filters and follows live direction.
===============================================================================
"""

# Import the signal functions from your engines
from sysmktpxy import get_signal      # Direction engine (UP / DOWN)
from sysstrndpxy import calculate_supertrend  # Structural engine (BUY / SELL / BULL / BEAR / SIDE)
from syscnfgpxy import TICKER
import pandas as pd
from datetime import datetime
import pytz

def get_entry_signal(df=None):
    """
    Advanced routing pipeline mapping structural trend regimes against execution signals.
    Exits follow live direction unconditionally. Entries utilize SuperTrend filtering, 
    while SIDE state lets direction flow through completely unfiltered.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()

    if df is None or df.empty:
        return "NONE", "NONE"

    # 1. Extract the geometric movement direction (UP / DOWN)
    direction, _ = get_signal(df)

    # 2. Extract the true SuperTrend regime matrix state (BUY / SELL / BULL / BEAR / SIDE)
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

    # =========================================================================
    # MATRIX STATE NORMALIZATION LAYER (Strictly Force to BULL or BEAR internal keys)
    # =========================================================================
    normalized_regime = "NONE"
    if current_regime in ["BUY", "BULL", "HSIDE"]:
        normalized_regime = "BULL"
    if current_regime in ["SELL", "BEAR", "LSIDE"]:
        normalized_regime = "BEAR"

    entry_signal = "NONE"
    
    # =========================================================================
    # UNCONDITIONAL EXIT MAPPING (Restored to your original engine rules)
    # =========================================================================
    exit_signal = "BULL" if direction == "UP" else "BEAR"

    # =========================================================================
    # ENTRY FILTER MATRIX & PRIORITY LAYER
    # =========================================================================
    
    # --- TIER 1 PRIORITY: ABSOLUTE CROSSOVER MOMENTS ---
    if current_regime == "BUY":
        entry_signal = "OTMBUY" if is_morning_otm_window else "ATMBUY"
        
    elif current_regime == "SELL":
        entry_signal = "OTMSELL" if is_morning_otm_window else "ATMSELL"

    # --- TIER 2 PRIORITY: PERSISTENT CONTINUATION STATES ---
    elif normalized_regime == "BULL":
        # Check alignment: Geometric engine says UP while SuperTrend is BULL
        if direction == "UP":
            entry_signal = "OTMBUY" if is_morning_otm_window else "ATMBUY"   # Aligned -> Target ATM/OTM
        else:
            entry_signal = "BEAR"   # Misaligned / Protection Filter -> Target NTM

    elif normalized_regime == "BEAR":
        # Check alignment: Geometric engine says DOWN while SuperTrend is BEAR
        if direction == "DOWN":
            entry_signal = "OTMSELL" if is_morning_otm_window else "ATMSELL"  # Aligned -> Target ATM/OTM
        else:
            entry_signal = "BULL"  # Misaligned / Protection Filter -> Target NTM

    # --- TIER 3 PRIORITY: SIDE CHOPPY REGIME (UNFILTERED BYPASS) ---
    elif current_regime == "SIDE":
        # SIDE should not filter anything. Let direction dictate execution completely.
        if direction == "UP":
            entry_signal = "OTMBUY" if is_morning_otm_window else "ATMBUY"
        elif direction == "DOWN":
            entry_signal = "OTMSELL" if is_morning_otm_window else "ATMSELL"

    # Console Status Reporting Actions
    if entry_signal != "NONE":
        print(f"          SUPER: {current_regime} | MOVE: {direction}")
        print(f"       ENTRY: {entry_signal} | EXIT: {exit_signal}")

    return entry_signal, exit_signal

if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is not None:
        entry, ex = get_entry_signal(df)
        print("-" * 50)
        print(f"FINAL PROCESSED EXECUTION >> ENTRY: {entry} | EXIT: {ex}")

