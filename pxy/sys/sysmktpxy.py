# pxy_engine.py
import pandas as pd
import numpy as np
from sysdthapxy import fetch_yf_data 

DEBUG = True

def get_pxy_data(df):
    """
    Transforms raw OHLC data into pure Heikin-Ashi (HA) metrics.
    Ensures accurate live candle calculation by handling history recursively.
    """
    df = df.copy()
    raw_open = df['Open'].values
    raw_high = df['High'].values
    raw_low = df['Low'].values
    raw_close = df['Close'].values
    
    n = len(df)
    ha_open = np.zeros(n)
    ha_close = np.zeros(n)

    # 1. Pure HA Close (Average of current OHLC)
    ha_close = (raw_open + raw_high + raw_low + raw_close) / 4.0

    # 2. Pure HA Open (Recursive Formula)
    ha_open[0] = (raw_open[0] + raw_close[0]) / 2.0
    for i in range(1, n):
        ha_open[i] = (ha_open[i-1] + ha_close[i-1]) / 2.0

    return ha_open, ha_close

def _print_console_bar(c1, c0, execution_state):
    """Renders the graphical console display profiling the active live running candle."""
    RST = "\033[0m"
    RED = "\033[91m"
    GRN = "\033[92m"
    YLW = "\033[1;93m"
    GRAY = "\033[90m"

    # Set up drawing limits based on the current open and close
    min_val = min(c1, c0) - 2
    max_val = max(c1, c0) + 2
    scale_width = 20

    def get_clean_bar(val):
        pos = int(((val - min_val) / (max_val - min_val)) * scale_width) if max_val != min_val else 1
        pos = max(1, pos)
        return ("█" * pos).ljust(scale_width)

    # HA Trend Color: Green if Close >= Open, Red if Close < Open
    candle_color = GRN if c0 >= c1 else RED

    rows = [
        (c1, f"HA_OPEN  C1-{int(c1)}", candle_color),
        (c0, f"HA_CLOSE C0-{int(c0)}", candle_color)
    ]

    # Sort rows so the higher price prints on top of the console graph
    rows.sort(key=lambda item: item[0], reverse=True)

    print(f"\n{YLW}=PURE HA GEOMETRIC ENGINE CONSOLE MONITOR(LIVE)={RST}")
    for val, label, color in rows:
        print(f"{color}{label}{RST} : {GRAY}[{color}{get_clean_bar(val)}{GRAY}]{RST}")
    print(f"{YLW}========================================{RST}")
    print(f"       CURRENT CANDLE DIRECTION : {YLW}{execution_state}{RST}")

def get_signal(df=None):
    """
    Evaluates the current live running candle's internal direction using pure HA.
    Returns: (entry_signal, exit_signal) -> ("BULL", "BULL"), ("BEAR", "BEAR"), or ("NONE", "NONE")
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    try:
        # Run pure Heikin-Ashi calculation across the historical chain
        ha_open, ha_close = get_pxy_data(df)
        
        # Pull the absolute newest, active live candle values
        c1 = float(ha_open[-1])   # Current Pure HA Open
        c0 = float(ha_close[-1])  # Current Pure HA Close

        # =====================================================================
        # 🛡️ EXCLUSIVE CONDITIONAL COMPARE MATRIX (CURRENT CANDLE DIRECTION)
        # =====================================================================
        if c0 > c1:
            execution_state = "BULL"
            
        elif c0 < c1:
            execution_state = "BEAR"
            
        else:
            # Flatline condition where open equals close exactly
            execution_state = "NONE"
        # =====================================================================

        # Render geometric profile layout 
        if DEBUG:
            _print_console_bar(c1, c0, execution_state)
            
        # Split twin signals directly to downstream pipelines
        return execution_state, execution_state

    except Exception as e:
        if DEBUG:
            print(f"Signal Processing Engine Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    df = fetch_yf_data()
    if df is not None and not df.empty:
        entry, ex = get_signal(df)
        print(f"SPLIT OUTPUT SIGNALS >> ENTRY: {entry} | EXIT: {ex}")

