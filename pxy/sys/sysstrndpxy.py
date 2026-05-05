import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# ==================================================
# GLOBAL CONFIG
# ==================================================
DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Master Engine Sync:
    Logic: VWAP Replacing ST Line
    Reference: Master Price P = (e1+e2+e3+e4)/4
    """
    df = df.copy()

    # --- FIX: Ensure Index is Datetime for .date grouping ---
    if not isinstance(df.index, pd.DatetimeIndex):
        # Look for typical date column names if index isn't already datetime
        for col in ['Date', 'Datetime', 'timestamp', 'time']:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])
                df.set_index(col, inplace=True)
                break
    # -------------------------------------------------------

    # 1. Master Price Engine (Synchronized)
    def get_p_series(df_slice):
        o, h, l, c = df_slice['Open'], df_slice['High'], df_slice['Low'], df_slice['Close']
        c1 = df_slice['Close'].shift(1)
        e1, e2, e3, e4 = c, (c1 + c) / 2, (c + o) / 2, (o + h + l + c) / 4
        return (e1 + e2 + e3 + e4) / 4

    df['P_Master'] = get_p_series(df)

    # 2. VWAP Calculation (Session Reset)
    # Now safe to call .date because index is forced to DatetimeIndex
    tp = (df['High'] + df['Low'] + df['Close']) / 3
    tpv = tp * df['Volume']
    group = df.index.date
    
    # Calculate Cumulative Sums with daily reset
    cum_tpv = tpv.groupby(group).cumsum()
    cum_vol = df['Volume'].groupby(group).cumsum()
    df['VWAP'] = cum_tpv / cum_vol

    # 3. Signal Mapping (P vs VWAP)
    size = len(df)
    signals = ["SIDE"] * size
    
    for i in range(1, size):
        p_curr, p_prev = df['P_Master'].iloc[i], df['P_Master'].iloc[i-1]
        v_curr, v_prev = df['VWAP'].iloc[i], df['VWAP'].iloc[i-1]

        if pd.isna(v_curr) or pd.isna(v_prev): 
            continue

        # Crossing Logic
        if p_curr > v_curr and p_prev <= v_prev:
            signals[i] = "BUY"
        elif p_curr < v_curr and p_prev >= v_prev:
            signals[i] = "SELL"
        else:
            signals[i] = "UP" if p_curr > v_curr else "DOWN"

    df['ST'] = df['VWAP']  # VWAP replaces the ST line
    df['ST_Trend'] = signals
    return df

def get_signal(df=None):
    if df is None: 
        df = fetch_yf_data()
    if df is None or df.empty: 
        return "NONE", 0.0
        
    df_st = calculate_supertrend(df)
    last = df_st.iloc[-1]
    return last['ST_Trend'], last['ST']




