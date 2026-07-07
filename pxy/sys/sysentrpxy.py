import numpy as np
import pandas as pd

def get_entry_signal(df=None):
    """
    Advanced routing pipeline driven by completed Heikin-Ashi candle transitions.
    
    Rules Engine:
    - GREEN to RED (completed)   -> Actionable ATMSELL
    - RED to GREEN (completed)   -> Actionable ATMBUY
    - GREEN to GREEN (completed) -> Non-actionable BULL
    - RED to RED (completed)     -> Non-actionable BEAR
    - No match / Flat Doji       -> NONE
    
    Args:
        df (pd.DataFrame, optional): Dataframe containing transformed Heikin-Ashi 
                                     Open, High, Low, and Close columns. 
                                     Defaults to fetching live data via system engine.

    Returns:
        tuple[str, str]: A pair of string tokens representing (entry_signal, exit_signal).
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
    if df is None or df.empty or len(df) < 4:
        return "NONE", "NONE"

    # =========================================================================
    # HEIKIN-ASHI CANDLE COLOR DETECTION ENGINE
    # =========================================================================
    # Check the color of the most recently completed candle (t-1)
    is_prev_green = df['Close'].iloc[-2] > df['Open'].iloc[-2]
    is_prev_red = df['Close'].iloc[-2] < df['Open'].iloc[-2]
    
    # Check the color of the candle before that (t-2) to capture the sequence transition
    is_prior_green = df['Close'].iloc[-3] > df['Open'].iloc[-3]
    is_prior_red = df['Close'].iloc[-3] < df['Open'].iloc[-3]

    # =========================================================================
    # PATTERN MATCHING ROUTING MATRIX
    # =========================================================================
    entry_signal = "NONE"
    
    # Rule 1: GREEN to RED transition (Completed) -> SELL
    if is_prior_green and is_prev_red:
        entry_signal = "ATMSELL"
        
    # Rule 2: RED to GREEN transition (Completed) -> BUY
    elif is_prior_red and is_prev_green:
        entry_signal = "ATMBUY"
        
    # Rule 3: GREEN to GREEN continuation (Completed) -> BULL
    elif is_prior_green and is_prev_green:
        entry_signal = "BULL"
        
    # Rule 4: RED to RED continuation (Completed) -> BEAR
    elif is_prior_red and is_prev_red:
        entry_signal = "BEAR"

    # Exit engine unconditionally maps to match the entry signal structure
    exit_signal = entry_signal

    # =========================================================================
    # SYSTEM OUTPUT TERMINAL LOGS
    # =========================================================================
    print(f" ENTRY: {entry_signal} | EXIT: {exit_signal}")
        
    return entry_signal, exit_signal



