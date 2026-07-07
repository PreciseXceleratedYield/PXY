import numpy as np
import pandas as pd

def get_entry_signal(df=None):
    """
    Advanced routing pipeline driven strictly by closed Heikin-Ashi candle color comparisons.
    
    Time-Based Execution Rules (IST):
    - From 09:15 to 12:15 IST -> Reversals convert to OTMBUY / OTMSELL
    - After 12:15 IST         -> Reversals convert to ATMBUY / ATMSELL
    
    Synchronized Rules Engine:
    - GREEN to RED (completed)   -> Entry: OTMSELL/ATMSELL | Exit: BEAR
    - RED to GREEN (completed)   -> Entry: OTMBUY/ATMBUY   | Exit: BULL
    - GREEN to GREEN (completed) -> Entry: BULL             | Exit: BULL
    - RED to RED (completed)     -> Entry: BEAR             | Exit: BEAR
    - No match / Flat Doji       -> Entry: NONE             | Exit: NONE
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
    if df is None or df.empty or len(df) < 4:
        return "NONE", "NONE"

    # =========================================================================
    # HEIKIN-ASHI CLOSED CANDLE COLOR DETECTION
    # =========================================================================
    # Candle (t-1): The most recently COMPLETED and closed candle
    prev_candle = df.iloc[-2]
    is_prev_green = prev_candle['Close'] > prev_candle['Open']
    is_prev_red = prev_candle['Close'] < prev_candle['Open']
    
    # Candle (t-2): The closed candle directly BEFORE the most recent one
    prior_candle = df.iloc[-3]
    is_prior_green = prior_candle['Close'] > prior_candle['Open']
    is_prior_red = prior_candle['Close'] < prior_candle['Open']

    # =========================================================================
    # TIME-BASED ROUTING ENGINE (IST DETECTION)
    # =========================================================================
    # Extract the time component from the most recently completed candle
    candle_time = prev_candle.name.time()
    
    # Convert time to total minutes from midnight for simple mathematical boundaries
    # 09:15 IST = 555 minutes | 12:15 IST = 735 minutes
    minutes_since_midnight = candle_time.hour * 60 + candle_time.minute
    
    # Check if the completed candle falls into the 9:15 AM - 12:15 PM window
    if 555 <= minutes_since_midnight <= 735:
        mode = "OTM"
    else:
        mode = "ATM"

    # =========================================================================
    # TWO-CANDLE COLOR PATTERN ROUTING MATRIX
    # =========================================================================
    entry_signal = "NONE"
    exit_signal = "NONE"
    
    # Rule 1: GREEN to RED transition (Two completed candles)
    if is_prior_green and is_prev_red:
        entry_signal = f"{mode}SELL"
        exit_signal = "BEAR"
        
    # Rule 2: RED to GREEN transition (Two completed candles)
    elif is_prior_red and is_prev_green:
        entry_signal = f"{mode}BUY"
        exit_signal = "BULL"
        
    # Rule 3: GREEN to GREEN continuation (Two completed candles)
    elif is_prior_green and is_prev_green:
        entry_signal = "BULL"
        exit_signal = "BULL"
        
    # Rule 4: RED to RED continuation (Completed)
    elif is_prior_red and is_prev_red:
        entry_signal = "BEAR"
        exit_signal = "BEAR"

    # =========================================================================
    # SYSTEM OUTPUT TERMINAL LOGS
    # =========================================================================
    print(f" TIME: {candle_time} | MODE: {mode} | ENTRY: {entry_signal} | EXIT: {exit_signal}")
        
    return entry_signal, exit_signal


