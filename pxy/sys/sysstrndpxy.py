# sysstrndpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False
JUMP_MODE = True  # True: Line jumps to Upper/Lower | False: Continuous line

def calculate_supertrend(df: pd.DataFrame, period=3, multiplier=3) -> pd.DataFrame:
    """ SuperTrend Engine with Jump/Continuous Switch """
    df = df.copy()
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(row['High'] - row['Low'], abs(row['High'] - row['previous_close']), abs(row['Low'] - row['previous_close'])), axis=1)
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
            
        prev_st_val = st[i-1]
        prev_trend = trend[i-1]
        ha_close = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        
        # 1. Determine Trend
        curr_trend = "UP" if ha_close > prev_st_val else "DOWN" if ha_close < prev_st_val else prev_trend
        
        # 2. THE JUMP SWITCH LOGIC
        if JUMP_MODE:
            # JUMPING: Line resets to actual upper/lower bound on flip
            if curr_trend == "UP":
                st[i] = lower if prev_trend == "DOWN" else max(lower, prev_st_val)
            else:
                st[i] = upper if prev_trend == "UP" else min(upper, prev_st_val)
        else:
            # CONTINUOUS (Original): Line sticks to prev_st until cross
            st[i] = max(lower, prev_st_val) if curr_trend == "UP" else min(upper, prev_st_val)
            
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"

    df_st = calculate_supertrend(df, period=3, multiplier=3)
    
    # --- CURRENT CANDLE (C) & PREVIOUS CANDLE (P) ---
    last_row = df_st.iloc[-1]
    prev_row = df_st.iloc[-2]
    
    ha_c_curr = (last_row['Open'] + last_row['High'] + last_row['Low'] + last_row['Close']) / 4
    ha_c_prev = (prev_row['Open'] + prev_row['High'] + prev_row['Low'] + prev_row['Close']) / 4
    
    st_curr = last_row['ST']
    st_prev = prev_row['ST']
    
    # --- 4-VALUE TRIGGER LOGIC ---
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
    mode_label = "JUMPING" if JUMP_MODE else "CONTINUOUS"
    print(f"MODE: {mode_label} | ST_SIG: {res} | MAJOR: {major}")



