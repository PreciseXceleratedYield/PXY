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
        close = df['Close'].iloc[i]
        
        if close > prev_st: curr_trend = "UP"
        elif close < prev_st: curr_trend = "DOWN"
        else: curr_trend = trend[i-1]
            
        if curr_trend == "UP": st[i] = max(lower, prev_st)
        if curr_trend == "DOWN": st[i] = min(upper, prev_st)
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    return df

def get_signal(df=None):
    if df is None: df = fetch_yf_data()
    if df is None or df.empty: return "NONE", "NONE"

    # Single Continuous Major Line (3:3)
    df_slow = calculate_supertrend(df, period=3, multiplier=3)

    # Current Price and Line Values
    curr_close = df_slow['Close'].iloc[-1]
    prev_close = df_slow['Close'].iloc[-2]
    curr_st = df_slow['ST'].iloc[-1]
    prev_st = df_slow['ST'].iloc[-2]
    
    slow_trend_status = df_slow['ST_Trend'].iloc[-1]

    # --- PRICE CROSSOVER LOGIC (ABSOLUTE PRIORITY) ---
    # BUY: Price was below ST line and now closed above it
    if prev_close <= prev_st and curr_close > curr_st:
        st_signal = "BUY"
    # SELL: Price was above ST line and now closed below it
    elif prev_close >= prev_st and curr_close < curr_st:
        st_signal = "SELL"
    # --- DIRECTIONAL POSITION ---
    elif curr_close > curr_st:
        st_signal = "UP"
    elif curr_close < curr_st:
        st_signal = "DOWN"
    else:
        st_signal = "NONE"

    if DEBUG_MODE:
        diff = curr_close - curr_st
        print(f"[DEBUG] PRICE:{curr_close:.2f} | MAJOR_ST:{curr_st:.2f} | DIFF:{diff:.2f}")

    return st_signal, slow_trend_status

if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)
    res, major = get_signal()
    color = Fore.GREEN if res in ["BUY", "UP"] else Fore.RED if res in ["SELL", "DOWN"] else Fore.WHITE
    print(f"{color}ST_SIG: {res:<15} MAJOR_TREND: {major}{Style.RESET_ALL}")


