# pxy_engine.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

USE_FORMING_CANDLE = False  # Hard-locked to completed candles for absolute production confirmation
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
    # 🔥 SIGNAL ENGINE (PURE CLOSED STRUCTURE CONFIRMATIONS)
    # ==================================================
    signal_array = np.full(len(df), "none", dtype=object)
    
    for i in range(len(df)):
        if i < 2:
            continue
            
        c0 = float(df['c0_close'].iloc[i])
        c1 = float(df['c1_close'].iloc[i])
        c2 = float(df['c2_close'].iloc[i])
        
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
    # 🎨 COLOR PROCESSING (STRICT CLOSED PRICE RULES)
    # ==================================================
    is_green = (df['c0_close'] > df['c1_close']) | ((df['c0_close'] == df['c1_close']) & (df['c0_close'] > df['c2_close']))
    is_red   = (df['c0_close'] < df['c1_close']) | ((df['c0_close'] == df['c1_close']) & (df['c0_close'] < df['c2_close']))

    conditions = [is_green, is_red]
    choices = ["green", "red"]
    
    df["pxy_color"] = np.select(conditions, choices, default="gray")

    # ==================================================
    # 🛡️ PRODUCTION OUTPUT FILTER (GAP EXCLUSION CODES)
    # ==================================================
    # Slicing is executed safely here to drop the live running candle from the pipeline
    final_df = df.iloc[:-1].copy()
    
    pxy_close = final_df['Close'].copy()
    pxy_open = final_df['Open'].copy()
    pxy_color_series = final_df['pxy_color'].copy()

    return pxy_close, pxy_open, pxy_color_series, final_df


