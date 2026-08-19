import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

DEBUG = True

# --- MODE SWITCH ---
# "LIVE"   -> Uses live running candle [-1] vs previous closed [-2]
# "CLOSED" -> Uses last closed candle [-2] vs prior closed [-3]
CANDLE_MODE = "CLOSED"  

def get_pxy_data(df, mode="LIVE"):
    """
    Processes market OHLC values based on the switch.
    LIVE:   c0 = live candle [-1], c1 = closed candle [-2]
    CLOSED: c0 = closed candle [-2], c1 = historical candle [-3]
    """
    df = df.copy()
    raw_close = df['Close'].values
    
    if len(raw_close) < 3:
        # Fallback for small datasets to avoid indexing crashes
        c0 = float(raw_close[-1]) if len(raw_close) > 0 else 0.0
        c1 = float(raw_close[-2]) if len(raw_close) > 1 else c0
        return c1, c0

    if mode.upper() == "LIVE":
        c0 = float(raw_close[-1])   # Live running candle (-1)
        c1 = float(raw_close[-2])   # Last closed candle (-2)
    else:  # CLOSED mode
        c0 = float(raw_close[-2])   # Last closed candle (-2)
        c1 = float(raw_close[-3])   # Prior closed candle (-3)
        
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
    
    # Map visual labels dynamically to match selected logic
    if mode.upper() == "LIVE":
        label_c1 = "CLSD -2"
        label_c0 = "LIVE -1"
    else:
        label_c1 = "HIST -3"
        label_c0 = "CLSD -2"
    
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
        
    print(f"\n{YLW}====== PXY MONITOR [{mode.upper()}] {indicator} ======={RST}")
    for val, label, color in rows:
        print(f" {color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{YLW}=========================================={RST}")

def get_signal(df=None, mode="LIVE"):
    """Evaluates the direction based on chosen candle mode."""
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"
        
    try:
        c1, c0 = get_pxy_data(df, mode=mode)
        
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
        entry, ex = get_signal(df, mode=CANDLE_MODE)
        print(f"OUT >> ENTRY: {entry:<4} | EXIT: {ex:<4}")

