# sysstrndpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data

# ==================================================
# DEBUG CONFIG
# ==================================================
DEBUG_MODE = True  # Set to False to hide line values

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
        
        # Explicit Trend Logic
        if close > prev_st: curr_trend = "UP"
        elif close < prev_st: curr_trend = "DOWN"
        else: curr_trend = trend[i-1]
            
        # Continuous Trailing Support/Resistance
        if curr_trend == "UP": st[i] = max(lower, prev_st)
        if curr_trend == "DOWN": st[i] = min(upper, prev_st)
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    df.drop(columns=['previous_close'], inplace=True)
    return df

def get_signal(df=None):
    """
    Priority Logic:
    1. BUY/SELL: Exact candle where Minor (1:1) crosses Major (3:3).
    2. UP: Minor is above Major.
    3. DOWN: Minor is below Major.
    """
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", "NONE"

    # Hardcoded Continuous Lines
    df_fast = calculate_supertrend(df, period=1, multiplier=1) # MINOR
    df_slow = calculate_supertrend(df, period=3, multiplier=3) # MAJOR

    f_curr, f_prev = df_fast['ST'].iloc[-1], df_fast['ST'].iloc[-2]
    s_curr, s_prev = df_slow['ST'].iloc[-1], df_slow['ST'].iloc[-2]
    
    slow_trend_status = df_slow['ST_Trend'].iloc[-1]

    # --- CROSSOVER TRIGGER (ONE-CANDLE) ---
    if f_prev <= s_prev and f_curr > s_curr:
        st_signal = "BUY"
    elif f_prev >= s_prev and f_curr < s_curr:
        st_signal = "SELL"
    # --- DIRECTIONAL POSITION ---
    elif f_curr > s_curr:
        st_signal = "UP"
    elif f_curr < s_curr:
        st_signal = "DOWN"
    else:
        st_signal = "NONE"

    if DEBUG_MODE:
        diff = f_curr - s_curr
        print(f"[DEBUG] MINOR:{f_curr:.2f} | MAJOR:{s_curr:.2f} | DIFF:{diff:.2f}")

    return st_signal, slow_trend_status

# ==================================================
# DASHBOARD
# ==================================================
if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)

    df_raw = fetch_yf_data()
    if df_raw is not None and not df_raw.empty:
        st_sig, major_t = get_signal(df_raw)
        
        # Color Assignment
        color = Fore.WHITE
        if st_sig in ["BUY", "UP"]: color = Fore.GREEN
        elif st_sig in ["SELL", "DOWN"]: color = Fore.RED

        # 42 Width Format
        left = f"ST_SIG: {st_sig}"
        right = f"MAJOR: {major_t}"
        print(f"{color}{left:<21}{right:>21}{Style.RESET_ALL}")
    else:
        print("Error: No Data")
