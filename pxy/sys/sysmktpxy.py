import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data
# Corrected import path to target your system module file name
from sysstrndpxy import calculate_supertrend 

DEBUG = True

def get_pxy_data(df):
    """
    Processes market values dynamically based on Supertrend zone classification.
    - 'SIDE': Returns raw close prices.
    - 'BULL'/'BEAR': Transforms close to (Open + Close) / 2 for analysis.
    """
    df = df.copy()
    
    opens = df['Open'].to_numpy()
    closes = df['Close'].to_numpy()
    trends = df['ST_Trend'].to_numpy()
    
    length = len(df)
    if length == 0:
        return 0.0, 0.0

    def calculate_candle_value(idx):
        trend = trends[idx]
        # If trend is active (BULL/BEAR), apply OC/2 transformation mechanics
        if trend in ['BULL', 'BEAR']:
            return float((opens[idx] + closes[idx]) / 2.0)
        # If trend is neutral (SIDE), keep the original raw Close price
        return float(closes[idx])

    c0 = calculate_candle_value(-1)
    c1 = calculate_candle_value(-2) if length > 1 else c0
    
    return c1, c0

def _print_console_bar(c1, c0, execution_state):
    """Renders the display profiling within a strict 42-char layout block using transformed mechanics."""
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

    # Labels represent transformed mechanical fields (TRN) for clarity
    rows = [
        (c1, f"PREV C1:{int(c1):<5}", candle_color),
        (c0, f"RUN  C0:{int(c0):<5}", candle_color)
    ]
    rows.sort(key=lambda item: item[0], reverse=True)

    if execution_state == "BULL":
        indicator = "🟢"
    elif execution_state == "BEAR":
        indicator = "🔴"
    else:
        indicator = "⚪"

    print(f"\n{YLW}====== PXY MONITOR LIVE ENGINE  {indicator}  ======={RST}")
    for val, label, color in rows:
        print(f"     {color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{YLW}=========================================={RST}")

def get_signal(df=None):
    """
    Evaluates the live execution state based on zone-transformed conditions.
    Returns: (entry_signal, exit_signal)
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    try:
        # Enrich the DataFrame with the 3-Zone Market Classifier from sysstrndpxy
        df = calculate_supertrend(df)
        
        # Unpack the dynamically transformed values (c1, c0 reflect the raw close OR OC/2 mechanics)
        c1, c0 = get_pxy_data(df)

        if c0 > c1:
            execution_state = "BULL"
        elif c0 < c1:
            execution_state = "BEAR"
        else:
            execution_state = "NONE"

        if DEBUG:
            _print_console_bar(c1, c0, execution_state)
            
        return execution_state, execution_state

    except Exception as e:
        if DEBUG:
            err_msg = str(e)[:25]
            print(f"Engine Err: {err_msg:<25}")
        return "NONE", "NONE"

if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_signal(df)
        print(f"OUT >> ENTRY: {entry:<4} | EXIT: {ex:<4}")

