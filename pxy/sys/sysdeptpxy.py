import pandas as pd
import numpy as np

# ANSI colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def get_p_series(df):
    """Calculates the P (Master Price) for the entire dataframe."""
    c = df['Close']
    o = df['Open']
    h = df['High']
    l = df['Low']
    c1 = df['Close'].shift(1)
    
    e1, e2 = c, (c1 + c) / 2
    e3, e4 = (c + o) / 2, (o + h + l + c) / 4
    
    return ((e1 + e2 + e3 + e4) / 4).round(4)

def get_candle_visual(df=None, last_n=42):
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return ""

    # 1. Calculate P instead of HA
    p_vals = get_p_series(df)
    
    # 2. Direction logic: Current P > Previous P
    # We use shift(1) to compare against the previous bar
    is_up = p_vals > p_vals.shift(1)
    
    # 3. VISUAL STREAM
    # / = P rising, \ = P falling
    subset = is_up.iloc[-last_n:]
    visual = "".join([
        f"{GREEN}/{RESET}" if val else f"{RED}\{RESET}" 
        for val in subset
    ])
    
    return visual

# -------- Self-test --------
if __name__ == "__main__":
    print("\nP-MASTER VISUAL STREAM:")
    print(get_candle_visual())

