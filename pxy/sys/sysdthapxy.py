# pxy_engine.py
import pandas as pd
import numpy as np
from sysstrndpxy import fetch_yf_data  # Note: Points to your file containing Mode 0

# ⚡ LIVE ENFORCEMENT ACTIVATED: Set to True to stream active forming bars dynamically
USE_FORMING_CANDLE = True  
CANDLE_STYLE = "MODE_0_PURE"

def get_pxy_data(tickerSymbol=None, df=None):
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return None, None, None, pd.DataFrame()
        
    # Safeguard: Separate processing safely from global reference memory
    df = df.copy()
        
    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, pd.DataFrame()

    # ==================================================
    # 🎨 COLOR PROCESSING (STRICT MODE 0 PURE BINARY RULES)
    # ==================================================
    # Since Mode 0 transforms 'Open' and 'Close', we use its structural logic:
    # A candle is green if Close is >= the previous bar's 3/4 range level.
    prev_h = df['High'].shift(1)
    prev_l = df['Low'].shift(1)
    prev_range = prev_h - prev_l
    calc_three_quarter = prev_l + (prev_range * 0.75)

    # Every single candle is binary: either it is green, or it defaults to red
    is_green = df['Close'] >= calc_three_quarter
    
    conditions = [is_green]
    choices = ["green"]
    df["pxy_color"] = np.select(conditions, choices, default="red")

    # ==================================================
    # 🔥 SIGNAL ENGINE (PURE CANDLE COLOR STATE MATRIX)
    # ==================================================
    signal_array = np.full(len(df), "none", dtype=object)
    
    # Pre-extract color series for fast index looping
    color_v = df['pxy_color'].to_numpy()
    
    for i in range(len(df)):
        if i < 1:
            continue
            
        c0_color = color_v[i]     # Current candle color
        c1_color = color_v[i-1]   # Previous candle color
        
        # Rule Switch based purely on color changes
        if c1_color == "red" and c0_color == "green":
            signal_array[i] = "BUY"    # Color flipped from Red to Green
        elif c1_color == "green" and c0_color == "red":
            signal_array[i] = "SELL"   # Color flipped from Green to Red
        elif c1_color == "green" and c0_color == "green":
            signal_array[i] = "BULL"   # Remained Green (Continuation)
        elif c1_color == "red" and c0_color == "red":
            signal_array[i] = "BEAR"   # Remained Red (Continuation)

    df["pxy_signal"] = signal_array

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (CONNECTED SWITCH)
    # ==================================================
    if USE_FORMING_CANDLE:
        final_df = df.copy()
    else:
        final_df = df.iloc[:-1].copy()
    
    pxy_close = final_df['Close'].copy()
    pxy_open = final_df['Open'].copy()
    pxy_color_series = final_df['pxy_color'].copy()

    return pxy_close, pxy_open, pxy_color_series, final_df


