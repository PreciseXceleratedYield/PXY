import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

DEBUG = True

# --- NEW SWITCH ENGINE ---
# MODE = "CURRENT"  # Evaluates live running candle against previous
# MODE = "PAST"     # Evaluates historical closed candles based on PAST_INDEX
MODE = "PAST"    
PAST_INDEX = -2     # If MODE is "PAST", -2 means the last fully closed candle, -3 is the one before, etc.

def get_pxy_data(df, mode="CURRENT", past_index=-2):
    """
    Processes market OHLC candle values based on selected mode.
    CURRENT: c0 = live running close, c1 = last closed candle.
    PAST:    c0 = selected historic close, c1 = prior historic close.
    """
    df = df.copy()
    raw_close = df['Close'].values
    
    if len(raw_close) < 2:
        c0 = float(raw_close[-1]) if len(raw_close) > 0 else 0.0
        return c0, c0

    if mode.upper() == "CURRENT":
        c0 = float(raw_close[-1])   # Live running price
        c1 = float(raw_close[-2])   # Last static closed candle
    else:
        # Prevent index out of bounds errors on short dataframes
        idx = max(1, len(raw_close) + past_index) if past_index < 0 else past_index
        if idx >= len(raw_close): 
            idx = len(raw_close) - 1
            
        c0 = float(raw_close[idx])     # Historical candle target
        c1 = float(raw_close[idx - 1]) # Prior historical reference candle
        
    return c1, c0

def _print_console_bar(c1, c0, execution_state, mode):
    """Renders the display profiling within a strict 42-char layout block."""
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"
    
    min_val = min(c1, c0) - 2
    max_val = max(c1, c0) + 2
    scale_width = 10
    
    def get_clean_bar(val):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width) if max_val != min_val else 1
        pos = max(1, pos)
        return ("█" * pos).ljust(scale_width)
        
    candle_color = GRN if c0 >= c1 else RED
    
    label_c1 = "PREV C1" if mode == "CURRENT" else f"HIST C{-past_index}"
    label_c0 = "RUN C0 " if mode == "CURRENT" else f"HIST C{-past_index-1}"
    
    rows = [
        (c1, f"{label_c1}:{int(c1):<5}", candle_color),
        (c0, f"{label_c0}:{int(c0):<5}", candle_color)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)
    
    if execution_state == "BULL":
        indicator = "🟢"
    elif execution_state == "BEAR":
        indicator = "🔴"
    else:
        indicator = "⚪"
        
    print(f"\n{YLW}====== PXY MONITOR LIVE ENGINE {indicator} ======={RST}")
    for val, label, color in rows:
        print(f" {color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{YLW}=========================================={RST}")

def get_signal(df=None, mode="CURRENT", past_index=-2):
    """
    Evaluates the internal direction based on chosen mode.
    Returns: (entry_signal, exit_signal)
    """
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"
        
    try:
        c1, c0 = get_pxy_data(df, mode=mode, past_index=past_index)
        
        if c0 > c1:
            execution_state = "BULL"
        elif c0 < c1:
            execution_state = "BEAR"
        else:
            execution_state = "NONE"
            
        if DEBUG:
            _print_console_bar(c1, c0, execution_state, mode)
            
        return execution_state, execution_state
    except Exception as e:
        if DEBUG:
            err_msg = str(e)[:25]
            print(f"Engine Err: {err_msg:<25}")
        return "NONE", "NONE"

if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        # Run using your global configurations
        entry, ex = get_signal(df, mode=MODE, past_index=PAST_INDEX)
        print(f"MODE: {MODE} | OUT >> ENTRY: {entry:<4} | EXIT: {ex:<4}")

