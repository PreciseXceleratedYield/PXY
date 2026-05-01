import pandas as pd
import numpy as np

# ==================================================
# GLOBAL CONFIG
# ==================================================
MIN_BODY_CONFIRM = 1.0  # Threshold for surgical BUY/SELL

def calculate_supertrend_pxy(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine:
    Major Factor: ATR^2
    Minor Factor: (ATR^2) / 6
    Using Dynamic Recursive ATR (1/Alpha smoothing)
    """
    df = df.copy()
    # Drop NaNs to ensure calculation continuity
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close']).reset_index(drop=True)
    
    df['previous_close'] = df['Close'].shift(1)
    df['TR'] = df[['High', 'Low', 'Close', 'previous_close']].apply(
        lambda row: max(row['High'] - row['Low'], 
                        abs(row['High'] - row['previous_close']), 
                        abs(row['Low'] - row['previous_close'])), axis=1)
    df['HL2'] = (df['High'] + df['Low']) / 2
    
    st_maj = [0.0] * len(df)
    st_min = [0.0] * len(df)
    trend_maj = [""] * len(df)
    trend_min = [""] * len(df)
    dyn_atr = [0.0] * len(df)
    
    # Initialize first bar
    seed_atr_val = df['TR'].iloc[0] if len(df) > 0 else 1.0

    for i in range(len(df)):
        tr, hl2 = df['TR'].iloc[i], df['HL2'].iloc[i]
        # Heikin-Ashi Close for trend tracking
        ha_c = (df['Open'].iloc[i] + df['High'].iloc[i] + df['Low'].iloc[i] + df['Close'].iloc[i]) / 4

        if i == 0:
            dyn_atr[i] = seed_atr_val
            st_maj[i], st_min[i] = hl2, hl2
            trend_maj[i], trend_min[i] = "UP", "UP"
            continue
        
        # 1. DYNAMIC ATR CALCULATION (Recursive)
        prev_atr = dyn_atr[i-1]
        alpha = 1 / max(1, round(prev_atr))
        dyn_atr[i] = (alpha * tr) + (1 - alpha) * prev_atr
        atr = dyn_atr[i]
        
        # 2. PXY® FACTORS
        maj_f = atr * atr
        min_f = maj_f / 6
        
        # 3. MAJOR ST LOGIC
        curr_t_maj = "UP" if ha_c > st_maj[i-1] else "DOWN" if ha_c < st_maj[i-1] else trend_maj[i-1]
        if curr_t_maj == "UP":
            st_maj[i] = max(hl2 - maj_f, st_maj[i-1])
        else:
            st_maj[i] = min(hl2 + maj_f, st_maj[i-1])
        trend_maj[i] = curr_t_maj

        # 4. MINOR ST LOGIC
        curr_t_min = "UP" if ha_c > st_min[i-1] else "DOWN" if ha_c < st_min[i-1] else trend_min[i-1]
        if curr_t_min == "UP":
            st_min[i] = max(hl2 - min_f, st_min[i-1])
        else:
            st_min[i] = min(hl2 + min_f, st_min[i-1])
        trend_min[i] = curr_t_min

    df['ST_Maj'], df['ST_Min'] = st_maj, st_min
    return df

def get_pxy_signal(df):
    """
    Final Signal Mapping:
    - BUY/SELL: Crossing Minor ST with Body Confirmation
    - UP: ha_c > Minor > Major
    - DOWN: ha_c < Minor < Major
    - SIDE: All other scenarios
    """
    if df is None or len(df) < 2:
        return "NONE", 0, 0

    df_pxy = calculate_supertrend_pxy(df)
    last = df_pxy.iloc[-1]
    prev = df_pxy.iloc[-2]
    
    # Current values
    c_curr, o_curr = last['Close'], last['Open']
    min_curr, maj_curr = last['ST_Min'], last['ST_Maj']
    ha_c = (o_curr + last['High'] + last['Low'] + c_curr) / 4
    
    # Previous values for crossover detection
    c_prev, min_prev = prev['Close'], prev['ST_Min']
    
    body_len = abs(c_curr - o_curr)

    # --- 1. ACTION TRIGGERS (Crossovers) ---
    if c_curr > min_curr and c_prev <= min_prev and body_len >= MIN_BODY_CONFIRM:
        return "BUY", round(maj_curr, 2), round(min_curr, 2)
    if c_curr < min_curr and c_prev >= min_prev and body_len >= MIN_BODY_CONFIRM:
        return "SELL", round(maj_curr, 2), round(min_curr, 2)

    # --- 2. TREND ALIGNMENT STATES ---
    if ha_c > min_curr and min_curr > maj_curr:
        return "UP", round(maj_curr, 2), round(min_curr, 2)
    elif ha_c < min_curr and min_curr < maj_curr:
        return "DOWN", round(maj_curr, 2), round(min_curr, 2)
    else:
        return "SIDE", round(maj_curr, 2), round(min_curr, 2)

# Integration Point:
# from sysdtafpxy import fetch_yf_data 
# data = fetch_yf_data()
# signal, major, minor = get_pxy_signal(data)
if __name__ == "__main__":
    from sysdtafpxy import fetch_yf_data 
    
    # Fetch and process
    data = fetch_yf_data()
    signal, major, minor = get_pxy_signal(data)
    
    # Print results
    print("-" * 30)
    print(f"PXY® SIGNAL : {signal}")
    print(f"MAJOR ST    : {major}")
    print(f"MINOR ST    : {minor}")
    print("-" * 30)
