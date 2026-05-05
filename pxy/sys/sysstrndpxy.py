import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Master Engine Sync:
    Logic: Fixed 1:1 SuperTrend (ATR 1, Mult 1.0)
    Reference: Master Price P = (e1+e2+e3+e4)/4
    """
    df = df.copy()
    
    # 1. Master Price Engine (Synchronized with sysmktpxy.py)
    def get_p_series(df_slice):
        o = df_slice['Open']
        h = df_slice['High']
        l = df_slice['Low']
        c = df_slice['Close']
        c1 = df_slice['Close'].shift(1)
        
        e1 = c
        e2 = (c1 + c) / 2
        e3 = (c + o) / 2
        e4 = (o + h + l + c) / 4
        return (e1 + e2 + e3 + e4) / 4

    df['P_Master'] = get_p_series(df)
    
    # 2. SuperTrend 1:1 Pre-calculations (Based on Close)
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = np.maximum(df['High'] - df['Low'], 
               np.maximum(abs(df['High'] - df['previous_close']), 
                          abs(df['Low'] - df['previous_close'])))
    
    df['ATR_1'] = df['TR'] # 1-period ATR
    df['HL2'] = (df['High'] + df['Low']) / 2
    
    size = len(df)
    st_line = [0.0] * size
    trend_state = [1] * size 

    # 3. 1:1 Calculation Loop
    for i in range(size):
        curr_close = df['Close'].iloc[i]
        hl2 = df['HL2'].iloc[i]
        atr1 = df['ATR_1'].iloc[i]
        
        if i == 0:
            st_line[i] = hl2
            continue

        # Band Calculation (Multiplier 1.0)
        upper_band = hl2 + (1.0 * atr1)
        lower_band = hl2 - (1.0 * atr1)
        
        prev_st = st_line[i-1]
        
        # Trend Flip based on Close
        if curr_close > prev_st:
            trend_state[i] = 1
        elif curr_close < prev_st:
            trend_state[i] = -1
        else:
            trend_state[i] = trend_state[i-1]

        if trend_state[i] == 1:
            st_line[i] = max(lower_band, prev_st)
        else:
            st_line[i] = min(upper_band, prev_st)

    # 4. Signal Mapping (Using Master Price P vs ST Line)
    signals = ["SIDE"] * size
    for i in range(1, size):
        p_curr = df['P_Master'].iloc[i]
        p_prev = df['P_Master'].iloc[i-1]
        st_curr = st_line[i]
        st_prev = st_line[i-1]

        # Crossing Logic (Master Price P Crosses ST Line)
        if p_curr > st_curr and p_prev <= st_prev:
            signals[i] = "BUY"
        elif p_curr < st_curr and p_prev >= st_prev:
            signals[i] = "SELL"
        else:
            signals[i] = "UP" if p_curr > st_curr else "DOWN"

    df['ST'] = st_line
    df['ST_Trend'] = signals
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", 0.0
        
    df_st = calculate_supertrend(df)
    last = df_st.iloc[-1]
    return last['ST_Trend'], last['ST']



