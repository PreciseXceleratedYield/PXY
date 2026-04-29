# sysstrndpxy.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False
JUMP_MODE = False  # Continuous like Pine

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """ SuperTrend Engine - PERIOD = ATR | MULTIPLIER = ATR """
    df = df.copy()
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(row['High'] - row['Low'], abs(row['High'] - row['previous_close']), abs(row['Low'] - row['previous_close'])), axis=1)
    
    df['HL2'] = (df['High'] + df['Low']) / 2
    
    # Initialize containers
    st = [0.0] * len(df)
    trend = [""] * len(df)
    dyn_atr = [0.0] * len(df)
    
    # We need a seed ATR to start the dynamic calculation
    seed_atr = df['TR'].rolling(window=3, min_periods=1).mean()

    for i in range(len(df)):
        tr = df['TR'].iloc[i]
        hl2 = df['HL2'].iloc[i]
        
        # --- 1. DYNAMIC ATR CALCULATION (PERIOD = ATR) ---
        if i == 0:
            dyn_atr[i] = seed_atr.iloc[0]
        else:
            # Use previous ATR to define the current smoothing period
            # Period = max(1, round(previous_atr))
            curr_period = max(1, round(dyn_atr[i-1]))
            alpha = 1 / curr_period
            dyn_atr[i] = (alpha * tr) + (1 - alpha) * dyn_atr[i-1]

        # --- 2. DYNAMIC BANDS (MULTIPLIER = ATR) ---
        atr = dyn_atr[i]
        upper = hl2 + (atr * atr)
        lower = hl2 - (atr * atr)
        
        if i == 0:
            st[i], trend[i] = hl2, "UP"
            continue
            
        prev_st_val = st[i-1]
        prev_trend = trend[i-1]
        ha_close = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        
        # 3. Determine Trend
        curr_trend = "UP" if ha_close > prev_st_val else "DOWN" if ha_close < prev_st_val else prev_trend
        
        # 4. Continuous Logic
        if curr_trend == "UP":
            st[i] = max(lower, prev_st_val)
        else:
            st[i] = min(upper, prev_st_val)
            
        # 5. Rounding to One Decimal
        st[i] = round(st[i], 1)
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"
        
    # No longer passing period/multiplier as they are now internal & dynamic
    df_st = calculate_supertrend(df) 
    
    last_row = df_st.iloc[-1]
    prev_row = df_st.iloc[-2]
    
    ha_c_curr = (last_row['Open'] + last_row['High'] + last_row['Low'] + last_row['Close']) / 4
    ha_c_prev = (prev_row['Open'] + prev_row['High'] + prev_row['Low'] + prev_row['Close']) / 4
    
    st_curr, st_prev = last_row['ST'], prev_row['ST']
    
    if ha_c_prev <= st_prev and ha_c_curr > st_curr:
        st_signal = "BUY"
    elif ha_c_prev >= st_prev and ha_c_curr < st_curr:
        st_signal = "SELL"
    elif ha_c_curr > st_curr:
        st_signal = "UP"
    else:
        st_signal = "DOWN"
        
    return st_signal, last_row['ST_Trend']

if __name__ == "__main__":
    res, major = get_signal()
    print(f"ST_SIG: {res} | MAJOR: {major}")




