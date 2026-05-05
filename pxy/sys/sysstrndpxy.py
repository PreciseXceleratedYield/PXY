import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 1. ROBUST DATETIME INDEX FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)

    # 2. Master Price Engine
    def get_p_series(df_slice):
        o, h, l, c = df_slice['Open'], df_slice['High'], df_slice['Low'], df_slice['Close']
        c1 = c.shift(1)
        return (c + (c1 + c) / 2 + (c + o) / 2 + (o + h + l + c) / 4) / 4

    df['P_Master'] = get_p_series(df)

    # 3. Dynamic SMA Calculation (Period = Current ATR)
    # Calculate ATR (14) first
    high_low = df['High'] - df['Low']
    high_cp = np.abs(df['High'] - df['Close'].shift())
    low_cp = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean().fillna(5) # Default to 5 if NaN

    # Calculate SMA with Dynamic Period
    # Since rolling() requires a fixed integer, we use a loop-based approach for variable window
    p_master_vals = df['P_Master'].values
    atr_vals = df['ATR'].values
    size = len(df)
    sma_values = np.zeros(size)

    for i in range(size):
        # Current ATR defines the period (minimum 1)
        period = max(1, int(round(atr_vals[i])))
        start_idx = max(0, i - period + 1)
        # Average of P_Master over the dynamic window
        sma_values[i] = np.mean(p_master_vals[start_idx : i + 1])

    df['DYNAMIC_SMA'] = sma_values

    # 4. Signal Mapping (P vs Dynamic SMA)
    signals = ["SIDE"] * size
    s_vals = df['DYNAMIC_SMA'].values
    
    for i in range(1, size):
        if np.isnan(s_vals[i]) or np.isnan(p_master_vals[i]):
            continue
            
        if p_master_vals[i] > s_vals[i] and p_master_vals[i-1] <= s_vals[i-1]:
            signals[i] = "BUY"
        elif p_master_vals[i] < s_vals[i] and p_master_vals[i-1] >= s_vals[i-1]:
            signals[i] = "SELL"
        else:
            signals[i] = "UP" if p_master_vals[i] > s_vals[i] else "DOWN"

    # Maintain compatibility with existing ST/ST_Trend keys
    df['ST'] = df['DYNAMIC_SMA']
    df['ST_Trend'] = signals
    return df

def get_signal(df=None):
    if df is None:
        df = fetch_yf_data()
    if df is None or df.empty:
        return "NONE", 0.0
    try:
        df_st = calculate_supertrend(df)
        last = df_st.iloc[-1]
        return str(last['ST_Trend']), float(last['ST'])
    except Exception as e:
        print(f"Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print("\nDynamic SMA (Period = ATR) - Last 5 bars:")
        print(df_full[['P_Master', 'ST', 'ST_Trend', 'ATR']].tail(5))




