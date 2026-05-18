import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

USE_FORMING_CANDLE = True
CANDLE_STYLE = "HA"

def get_ha_data(tickerSymbol=None, df=None):
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return None, None, None, df
        
    if not USE_FORMING_CANDLE:
        df = df.iloc[:-1].copy()
    else:
        df = df.copy()
        
    required_cols = ['Open', 'High', 'Low', 'Close']
    for col in required_cols:
        if col not in df.columns:
            return None, None, None, df

    # ==================================================
    # 🔥 BACKWARD COMPATIBLE FALLBACK VARIABLES
    # ==================================================
    # Maintained to protect the legacy functional signature 
    ha_close = (df['Open'] + df['Close']) / 2
    ha_open = df['Open'].copy()
    ha_color = pd.Series("none", index=df.index, dtype='object')

    # ==================================================
    # 🔥 SIGNAL ENGINE (PURE CLOSE PRICE AND FLAT MATRIX RECONCILIATION)
    # ==================================================
    signal = pd.Series("none", index=df.index, dtype='object')
    
    # Pre-compute lookbacks to maintain fast performance profiles
    df['c0_close'] = df['Close']
    df['c1_close'] = df['Close'].shift(1)
    df['c2_close'] = df['Close'].shift(2)
    
    last_signal = None
    hold_count = 0
    
    for i in range(len(df)):
        if i < 2:
            signal.iloc[i] = "none"
            continue
            
        c0 = float(df['c0_close'].iloc[i])
        c1 = float(df['c1_close'].iloc[i])
        c2 = float(df['c2_close'].iloc[i])
        
        new_signal = None
        
        # Rule Trigger A: Flat execution state detected (C1 == C0)
        if c1 == c0:
            if c0 > c2:
                new_signal = "BUY"    # Macro breakout over C2
            elif c0 < c2:
                new_signal = "SELL"   # Macro breakdown below C2
                
        # Rule Trigger B: Standard directional movement vectors
        else:
            if (c1 > c2) and (c0 > c1):
                new_signal = "BULL"   # Upward Continuation Matrix
                
            elif (c1 < c2) and (c0 < c1):
                new_signal = "BEAR"   # Downward Continuation Matrix
                
            elif (c1 < c2 or c1 == c2) and (c0 > c1):
                new_signal = "BUY"    # Structural V Pattern / Flat Rebound
                
            elif (c1 > c2 or c1 == c2) and (c0 < c1):
                new_signal = "SELL"   # Structural Inverted V / Flat Drop
                
        # ---------------- HOLD LAYER LOGIC ----------------
        if new_signal:
            last_signal = new_signal
            hold_count = 2
            signal.iloc[i] = new_signal
        elif hold_count > 0:
            signal.iloc[i] = last_signal
            hold_count -= 1
        else:
            signal.iloc[i] = "none"

    # Inject safely back into dataframe to keep downstreams secure
    df["ha_signal"] = signal
    return ha_close, ha_open, ha_color, df

