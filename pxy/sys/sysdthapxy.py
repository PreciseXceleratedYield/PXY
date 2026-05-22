# pxy_engine.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ⚡ LIVE ENFORCEMENT ACTIVATED: Set to True to stream active forming bars dynamically
USE_FORMING_CANDLE = True  
CANDLE_STYLE = "CLOSE_MOMENTUM"

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
    # ⚡ DATA MATRIX PRE-COMPUTATION
    # ==================================================
    df['c0_close'] = df['Close']          
    df['c1_close'] = df['Close'].shift(1) 
    df['c2_close'] = df['Close'].shift(2) 

    # ==================================================
    # 🔥 SIGNAL ENGINE (REAL-TIME STREAM EVALUATION)
    # ==================================================
    signal_array = np.full(len(df), "none", dtype=object)
    
    # Pre-extract numpy vectors for fast processing loops
    c0_v = df['c0_close'].to_numpy()
    c1_v = df['c1_close'].to_numpy()
    c2_v = df['c2_close'].to_numpy()
    
    for i in range(len(df)):
        if i < 2:
            continue
            
        c0 = float(c0_v[i])
        c1 = float(c1_v[i])
        c2 = float(c2_v[i])
        
        # Rule Trigger A: Flat execution state detected (C1 == C0)
        if c1 == c0:
            if c0 > c2:
                signal_array[i] = "BUY"    
            elif c0 < c2:
                signal_array[i] = "SELL"   
                
        # Rule Trigger B: Standard directional movement vectors
        else:
            if (c1 > c2) and (c0 > c1):
                signal_array[i] = "BULL"   
            elif (c1 < c2) and (c0 < c1):
                signal_array[i] = "BEAR"   
            elif (c1 < c2 or c1 == c2) and (c0 > c1):
                signal_array[i] = "BUY"    
            elif (c1 > c2 or c1 == c2) and (c0 < c1):
                signal_array[i] = "SELL"   

    df["pxy_signal"] = signal_array

    # ==================================================
    # 🎨 COLOR PROCESSING (STRICT PRICE RULES)
    # ==================================================
    is_green = (df['c0_close'] > df['c1_close']) | ((df['c0_close'] == df['c1_close']) & (df['c0_close'] > df['c2_close']))
    is_red   = (df['c0_close'] < df['c1_close']) | ((df['c0_close'] == df['c1_close']) & (df['c0_close'] < df['c2_close']))

    conditions = [is_green, is_red]
    choices = ["green", "red"]
    
    df["pxy_color"] = np.select(conditions, choices, default="gray")

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (CONNECTED SWITCH)
    # ==================================================
    # If USE_FORMING_CANDLE is True, process the absolute latest live ticking bar.
    # If False, drop the incomplete bar to stick to closed historical bars only.
    if USE_FORMING_CANDLE:
        final_df = df.copy()
    else:
        final_df = df.iloc[:-1].copy()
    
    pxy_close = final_df['Close'].copy()
    pxy_open = final_df['Open'].copy()
    pxy_color_series = final_df['pxy_color'].copy()

    return pxy_close, pxy_open, pxy_color_series, final_df



