# sysstrndpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data

# ==================================================
# DEBUG CONFIG
# ==================================================
DEBUG_MODE = True 

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
        
        # Standard HA Close Calculation
        ha_close = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4
        
        # Trend Logic: HA Close vs Previous ST Line
        if ha_close > prev_st: 
            curr_trend = "UP"
        elif ha_close < prev_st: 
            curr_trend = "DOWN"
        else: 
            curr_trend = trend[i-1]
            
        # Continuous Trailing Logic (No Jumps)
        if curr_trend == "UP": 
            st[i] = max(lower, prev_st)
        else: 
            st[i] = min(upper, prev_st)
            
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    return df

def get_signal(df=None):
    if df is None: df = fetch_yf_data()
    if df is None or df.empty: return "NONE", "NONE"

    # Calculate 3:3 Continuous ST
    df_st = calculate_supertrend(df, period=3, multiplier=3)

    # HA Price for Current & Previous
    ha_curr = (df_st['Open'].iloc[-1] + df_st['High'].iloc[-1] + df_st['Low'].iloc[-1] + df_st['Close'].iloc[-1]) / 4
    ha_prev = (df_st['Open'].iloc[-2] + df_st['High'].iloc[-2] + df_st['Low'].iloc[-2] + df_st['Close'].iloc[-2]) / 4
    
    curr_st = df_st['ST'].iloc[-1]
    prev_st = df_st['ST'].iloc[-2]
    
    st_signal = "NONE"

    # --- STANDARD HA CROSSOVER (TRIGGER ON HA_CLOSE FLIP) ---
    if ha_prev <= prev_st and ha_curr > curr_st:
        st_signal = "BUY"
    elif ha_prev >= prev_st and ha_curr < curr_st:
        st_signal = "SELL"
    elif ha_curr > curr_st:
        st_signal = "UP"
    elif ha_curr < curr_st:
        st_signal = "DOWN"

    if DEBUG_MODE:
        diff = ha_curr - curr_st
        print(f"[DEBUG] HA_C:{ha_curr:.2f} | ST:{curr_st:.2f} | DIFF:{diff:.2f} | SIG:{st_signal}")

    return st_signal, df_st['ST_Trend'].iloc[-1]

if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)
    res, major = get_signal()
    
    color = Fore.GREEN if res in ["BUY", "UP"] else Fore.RED if res in ["SELL", "DOWN"] else Fore.WHITE
    print(f"{color}ST_SIG: {res:<15} MAJOR: {major}{Style.RESET_ALL}")



