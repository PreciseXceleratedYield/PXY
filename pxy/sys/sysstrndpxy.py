# sysstrndpxy.py
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False
JUMP_MODE = False
MIN_BODY_CONFIRM = 1.0  # Body length required for BUY/SELL

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """ PXY® Engine: Major (ATR^2) and Minor (Major/6) """
    df = df.copy()
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(row['High'] - row['Low'], 
                        abs(row['High'] - row['previous_close']), 
                        abs(row['Low'] - row['previous_close'])), axis=1)
    df['HL2'] = (df['High'] + df['Low']) / 2

    # Containers
    st_maj = [0.0] * len(df)
    st_min = [0.0] * len(df)
    trend_maj = [""] * len(df)
    dyn_atr = [0.0] * len(df)
    
    seed_atr = df['TR'].rolling(window=3, min_periods=1).mean()

    for i in range(len(df)):
        tr, hl2 = df['TR'].iloc[i], df['HL2'].iloc[i]
        ha_close = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4

        if i == 0:
            dyn_atr[i] = seed_atr.iloc[0] if not pd.isna(seed_atr.iloc[0]) else 1.0
            st_maj[i], st_min[i] = hl2, hl2
            trend_maj[i] = "UP"
            continue
        
        # 1. DYNAMIC ATR
        prev_atr = dyn_atr[i-1]
        alpha = 1 / max(1, round(prev_atr))
        dyn_atr[i] = (alpha * tr) + (1 - alpha) * prev_atr
        
        # 2. PXY® FACTORS
        maj_f = dyn_atr[i] * dyn_atr[i]
        min_f = maj_f / 6
        
        # 3. MAJOR ST LOGIC (Matches original return structure)
        curr_trend = "UP" if ha_close > st_maj[i-1] else "DOWN" if ha_close < st_maj[i-1] else trend_maj[i-1]
        st_maj[i] = max(hl2 - maj_f, st_maj[i-1]) if curr_trend == "UP" else min(hl2 + maj_f, st_maj[i-1])
        trend_maj[i] = curr_trend

        # 4. MINOR ST LOGIC
        prev_min = st_min[i-1]
        min_trend = "UP" if ha_close > prev_min else "DOWN" if ha_close < prev_min else "UP"
        st_min[i] = max(hl2 - min_f, prev_min) if min_trend == "UP" else min(hl2 + min_f, prev_min)

    df['ST'], df['ST_Trend'] = st_maj, trend_maj # Maintain original column names
    df['ST_Min'] = st_min
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"

    df_st = calculate_supertrend(df)
    last = df_st.iloc[-1]
    prev = df_st.iloc[-2]
    
    # Body Confirmation Logic
    body_len = abs(last['Close'] - last['Open'])
    ha_c = (last['Open'] + last['High'] + last['Low'] + last['Close']) / 4
    
    st_curr, st_prev = last['ST'], prev['ST']
    min_curr, min_prev = last['ST_Min'], prev['ST_Min']
    c_curr, c_prev = last['Close'], prev['Close']

    # 1. ACTION TRIGGERS (Crossovers + Body Confirm)
    if c_curr > min_curr and c_prev <= min_prev and body_len >= MIN_BODY_CONFIRM:
        res = "BUY"
    elif c_curr < min_curr and c_prev >= min_prev and body_len >= MIN_BODY_CONFIRM:
        res = "SELL"
    # 2. TREND STATES
    elif ha_c > min_curr and min_curr > st_curr:
        res = "UP"
    elif ha_c < min_curr and min_curr < st_curr:
        res = "DOWN"
    else:
        res = "SIDE"

    return res, last['ST_Trend']

if __name__ == "__main__":
    res, major_trend = get_signal()
    print(f"ST_SIG: {res} | MAJOR_TREND: {major_trend}")
