import numpy as np
import pandas as pd

def get_entry_signal(df=None):
    """
    Advanced routing pipeline driven strictly by closed Heikin-Ashi candle color comparisons.
    
    This engine evaluates data PURELY based on the color transition of the two most 
    recently completed candles. It applies no external filters or secondary conditions.
    
    Synchronized Rules Engine:
    - GREEN to RED (completed)   -> Entry: ATMSELL | Exit: BEAR
    - RED to GREEN (completed)   -> Entry: ATMBUY  | Exit: BULL
    - GREEN to GREEN (completed) -> Entry: BULL    | Exit: BULL
    - RED to RED (completed)     -> Entry: BEAR    | Exit: BEAR
    - No match / Flat Doji       -> Entry: NONE    | Exit: NONE
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
    if df is None or df.empty or len(df) < 4:
        return "NONE", "NONE"

    # =========================================================================
    # PURE HEIKIN-ASHI CLOSED CANDLE COLOR DETECTION
    # =========================================================================
    # Candle (t-1): The most recently COMPLETED and closed candle
    is_prev_green = df['Close'].iloc[-2] > df['Open'].iloc[-2]
    is_prev_red = df['Close'].iloc[-2] < df['Open'].iloc[-2]
    
    # Candle (t-2): The closed candle directly BEFORE the most recent one
    is_prior_green = df['Close'].iloc[-3] > df['Open'].iloc[-3]
    is_prior_red = df['Close'].iloc[-3] < df['Open'].iloc[-3]

    # =========================================================================
    # TWO-CANDLE COLOR PATTERN ROUTING MATRIX
    # =========================================================================
    entry_signal = "NONE"
    exit_signal = "NONE"
    
    # Rule 1: GREEN to RED transition (Two completed candles)
    if is_prior_green and is_prev_red:
        entry_signal = "ATMSELL"
        exit_signal = "BEAR"
        
    # Rule 2: RED to GREEN transition (Two completed candles)
    elif is_prior_red and is_prev_green:
        entry_signal = "ATMBUY"
        exit_signal = "BULL"
        
    # Rule 3: GREEN to GREEN continuation (Two completed candles)
    elif is_prior_green and is_prev_green:
        entry_signal = "BULL"
        exit_signal = "BULL"
        
    # Rule 4: RED to RED continuation (Two completed candles)
    elif is_prior_red and is_prev_red:
        entry_signal = "BEAR"
        exit_signal = "BEAR"

    # =========================================================================
    # SYSTEM OUTPUT TERMINAL LOGS
    # =========================================================================
    print(f" ENTRY: {entry_signal} | EXIT: {exit_signal}")
        
    return entry_signal, exit_signal


