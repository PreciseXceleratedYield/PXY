# sysstrndpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False
JUMP_MODE = False  # Continuous line like Pine

def calculate_supertrend(df: pd.DataFrame, period=3, multiplier=3) -> pd.DataFrame:
    """ SuperTrend Engine - UPDATED TO ATR-SQUARED CONTINUOUS """
    df = df.copy()
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(row['High'] - row['Low'], abs(row['High'] - row['previous_close']), abs(row['Low'] - row['previous_close'])), axis=1)
    
    # Pine-matching RMA logic
    df['ATR'] = df['TR'].ewm(alpha=1/period, adjust=False).mean()
    df['HL2'] = (df['High'] + df['Low']) / 2
    
    st = [0.0] * len(df)
    trend = [""] * len(df)
    
    for i in range(len(df)):
        hl2, atr = df['HL2'].iloc[i], df['ATR'].iloc[i]
        
        # --- ATR-SQUARED LOGIC (multiplier = atr) ---
        upper, lower = hl2 + (atr * atr), hl2 - (atr * atr)
        
        if i == 0 or pd.isna(atr):
            st[i], trend[i] = hl2, "UP"
            continue
            
        prev_st_val = st[i-1]
        prev_trend = trend[i-1]
        ha_close = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        
        # 1. Determine Trend
        curr_trend = "UP" if ha_close > prev_st_val else "DOWN" if ha_close < prev_st_val else prev_trend
        
        # 2. CONTINUOUS LOGIC (JUMP_MODE False)
        if curr_trend == "UP":
            st[i] = max(lower, prev_st_val)
        else:
            st[i] = min(upper, prev_st_val)
            
        # ROUND TO ONE DECIMAL AS IN PINE
        st[i] = round(st[i], 1)
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"
        
    # Keep period=3, multiplier is ignored in the new logic
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
    print(f"ST_SIG: {res} | MAJOR: {major}")




