# sysstrndpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data

def calculate_supertrend(df: pd.DataFrame, period=3, multiplier=3) -> pd.DataFrame:
    """ Continuous SuperTrend (Pine-matching logic) """
    df = df.copy()
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(row['High'] - row['Low'], 
                        abs(row['High'] - row['previous_close']), 
                        abs(row['Low'] - row['previous_close'])), axis=1)
    
    # RMA matching Pine Script
    df['ATR'] = df['TR'].ewm(alpha=1/period, adjust=False).mean()
    df['HL2'] = (df['High'] + df['Low']) / 2
    
    st = [0.0] * len(df)
    trend = [""] * len(df)
    
    for i in range(len(df)):
        hl2, atr = df['HL2'].iloc[i], df['ATR'].iloc[i]
        upper, lower = hl2 + multiplier * atr, hl2 - multiplier * atr
        
        if i == 0 or pd.isna(atr):
            st[i], trend[i] = hl2, "UP"
            continue
        
        prev_st = st[i-1]
        close = df['Close'].iloc[i]
        
        # Explicit Trend Conditions
        if close > prev_st: curr_trend = "UP"
        elif close < prev_st: curr_trend = "DOWN"
        else: curr_trend = trend[i-1]
            
        # Continuous Trailing Logic
        if curr_trend == "UP": st[i] = max(lower, prev_st)
        if curr_trend == "DOWN": st[i] = min(upper, prev_st)
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    df.drop(columns=['previous_close'], inplace=True)
    return df

