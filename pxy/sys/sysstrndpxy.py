# sysstrndpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data

# ==================================================
# DEBUG CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame, period=3, multiplier=3) -> pd.DataFrame:
    """ Continuous SuperTrend (Pine-matching logic) """
    df = df.copy()
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(row['High'] - row['Low'], 
                        abs(row['High'] - row['previous_close']), 
                        abs(row['Low'] - row['previous_close'])), axis=1)
    
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
        ha_close = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        
        if ha_close > prev_st: curr_trend = "UP"
        elif ha_close < prev_st: curr_trend = "DOWN"
        else: curr_trend = trend[i-1]
            
        if curr_trend == "UP": st[i] = max(lower, prev_st)
        else: st[i] = min(upper, prev_st)
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    return df

def get_signal(df=None):
    if df is None: df = fetch_yf_data()
    if df is None or df.empty: return "NONE", "NONE"

    # Calculate 3:3 Continuous ST
    df_st = calculate_supertrend(df, period=3, multiplier=3)

    # --- CURRENT CANDLE (C) & PREVIOUS CANDLE (P) ---
    c_open, c_high, c_low, c_close = df_st['Open'].iloc[-1], df_st['High'].iloc[-1], df_st['Low'].iloc[-1], df_st['Close'].iloc[-1]
    p_open, p_high, p_low, p_close = df_st['Open'].iloc[-2], df_st['High'].iloc[-2], df_st['Low'].iloc[-2], df_st['Close'].iloc[-2]
    
    # HA Price for Early Detection (Body Midpoint vs Close)
    ha_c_curr = (c_open + c_high + c_low + c_close) / 4
    ha_c_prev = (p_open + p_high + p_low + p_close) / 4
    
    # Current ST Line
    st_curr = df_st['ST'].iloc[-1]
    st_prev = df_st['ST'].iloc[-2]
    
    st_signal = "NONE"

    # --- 1-MINUTE STICKY TRIGGER LOGIC ---
    # Detected EARLY: The moment HA Close flips the ST line
    # BUY: Prev was below/equal, Curr is above
    if ha_c_prev <= st_prev and ha_c_curr > st_curr:
        st_signal = "BUY"
    
    # SELL: Prev was above/equal, Curr is below
    elif ha_c_prev >= prev_st and ha_c_curr < st_curr:
        st_signal = "SELL"
        
    # --- CONTINUOUS FLOW (AFTER THE TRIGGER MINUTE) ---
    elif ha_c_curr > st_curr:
        st_signal = "UP"
    elif ha_c_curr < st_curr:
        st_signal = "DOWN"

    return st_signal, df_st['ST_Trend'].iloc[-1]

if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)
    res, major = get_signal()
    color = Fore.GREEN if res in ["BUY", "UP"] else Fore.RED if res in ["SELL", "DOWN"] else Fore.WHITE
    print(f"{color}ST_SIG: {res:<15} MAJOR: {major}{Style.RESET_ALL}")



