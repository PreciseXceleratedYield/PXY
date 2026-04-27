# sysstrndpxy.py
import pandas as pd
from sysdtafpxy import fetch_yf_data

def calculate_supertrend(df: pd.DataFrame, period=3, multiplier=3) -> pd.DataFrame:
    """ 
    Continuous SuperTrend (Pine-matching logic) 
    - No jumps: waits for price close to cross the line.
    - Smooth trailing: using max/min to prevent line from retreating.
    """
    df = df.copy()
    df['previous_close'] = df['Close'].shift(1)
    
    # -------- TRUE RANGE (RMA Basis) --------
    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(row['High'] - row['Low'], 
                        abs(row['High'] - row['previous_close']), 
                        abs(row['Low'] - row['previous_close'])), axis=1)
    
    # -------- ATR (MATCH PINE RMA) --------
    df['ATR'] = df['TR'].ewm(alpha=1/period, adjust=False).mean()
    df['HL2'] = (df['High'] + df['Low']) / 2
    
    st = [0.0] * len(df)
    trend = [""] * len(df)
    
    # -------- LOOP: CONTINUOUS TRAIL --------
    for i in range(len(df)):
        hl2, atr = df['HL2'].iloc[i], df['ATR'].iloc[i]
        upper, lower = hl2 + multiplier * atr, hl2 - multiplier * atr
        
        if i == 0 or pd.isna(atr):
            st[i], trend[i] = hl2, "UP"
            continue
        
        prev_st = st[i-1]
        close = df['Close'].iloc[i]
        
        # Explicit Trend Conditions (Price vs Line)
        if close > prev_st: 
            curr_trend = "UP"
        elif close < prev_st: 
            curr_trend = "DOWN"
        else: 
            curr_trend = trend[i-1]
            
        # Continuous Trailing (UP only moves up, DOWN only moves down)
        if curr_trend == "UP": 
            st[i] = max(lower, prev_st)
        if curr_trend == "DOWN": 
            st[i] = min(upper, prev_st)
            
        trend[i] = curr_trend
        
    df['ST'], df['ST_Trend'] = st, trend
    df.drop(columns=['previous_close'], inplace=True)
    return df

def get_signal(df=None):
    """
    Priority Engine: 1:1 Fast vs 3:3 Slow Crossover.
    Returns: (entry_signal, exit_signal)
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or df.empty:
        return "NONE", "NONE"

    # Hardcoded Continuous Lines
    df_fast = calculate_supertrend(df, period=1, multiplier=1)
    df_slow = calculate_supertrend(df, period=3, multiplier=3)

    f_curr, f_prev = df_fast['ST'].iloc[-1], df_fast['ST'].iloc[-2]
    s_curr, s_prev = df_slow['ST'].iloc[-1], df_slow['ST'].iloc[-2]
    
    slow_trend = df_slow['ST_Trend'].iloc[-1]

    # --- ONE-CANDLE CROSSOVER (ABSOLUTE PRIORITY) ---
    if f_prev <= s_prev and f_curr > s_curr:
        entry = "BUY"
    elif f_prev >= s_prev and f_curr < s_curr:
        entry = "SELL"
    # --- CONTINUOUS FLOW (IF NO CROSSOVER) ---
    elif f_curr > s_curr:
        entry = "UP"
    elif f_curr < s_curr:
        entry = "DOWN"
    else:
        entry = "NONE"

    return entry, slow_trend

# ==================================================
# IF MAIN: DASHBOARD OUTPUT
# ==================================================
if __name__ == "__main__":
    from colorama import Fore, Style, init
    init(autoreset=True)

    df_raw = fetch_yf_data()
    if df_raw is not None and not df_raw.empty:
        entry, slow_t = get_signal(df_raw)
        
        # Color Logic
        if entry in ["BUY", "UP"]:
            color = Fore.GREEN
        elif entry in ["SELL", "DOWN"]:
            color = Fore.RED
        else:
            color = Fore.WHITE

        # Format 42 Width
        left = f"ST PRIO:{entry}"
        right = f"SLOW:{slow_t}"
        line = f"{left:<21}{right:>21}"
        
        print(f"=== {df_raw['Datetime'].iloc[-1]} ===")
        print(f"{color}{line}{Style.RESET_ALL}")
    else:
        print("Waiting for data...")


