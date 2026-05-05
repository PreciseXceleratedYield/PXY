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
    Logic: Time Series Moving Average (TSMA) 9-Period
    Reference: Endpoint of 9-bar Linear Regression Line
    """
    df = df.copy()

    # 1. ROBUST DATETIME INDEX FIX
    if not isinstance(df.index, pd.DatetimeIndex):
        date_col = next((c for c in ['Date', 'Datetime', 'timestamp', 'time'] if c in df.columns), None)
        if date_col:
            df[date_col] = pd.to_datetime(df[date_col])
            df.set_index(date_col, inplace=True)

    # 2. Master Price Engine (Synchronized)
    def get_p_series(df_slice):
        o, h, l, c = df_slice['Open'], df_slice['High'], df_slice['Low'], df_slice['Close']
        c1 = c.shift(1)
        # Master Engine Price Logic
        return (c + (c1 + c) / 2 + (c + o) / 2 + (o + h + l + c) / 4) / 4

    df['P_Master'] = get_p_series(df)

    # 3. Pure NumPy Time Series Moving Average (9-Period)
    # Using the Least Squares Linear Regression Endpoint formula
    # TSMA Endpoint = Intercept + Slope * (Period - 1)
    p_vals = df['P_Master'].values
    size = len(df)
    tsma_vals = np.full(size, np.nan)
    period = 9

    # Pre-calculate x-axis constants for Linear Regression
    # x = [0, 1, 2, ..., 8]
    x = np.arange(period)
    sum_x = np.sum(x)
    sum_x2 = np.sum(x**2)
    denominator = (period * sum_x2) - (sum_x**2)

    for i in range(period - 1, size):
        y = p_vals[i - period + 1 : i + 1]
        if np.isnan(y).any():
            continue
        
        # Calculate Slope (m) and Intercept (b) using Least Squares
        sum_y = np.sum(y)
        sum_xy = np.sum(x * y)
        
        slope = (period * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / period
        
        # TSMA value is the predicted Y at the latest point (x = period-1)
        tsma_vals[i] = intercept + slope * (period - 1)

    df['TSMA_9'] = tsma_vals

    # 4. Signal Mapping (P_Master vs TSMA_9)
    signals = ["SIDE"] * size
    t_vals = df['TSMA_9'].values
    
    for i in range(1, size):
        p_curr, p_prev = p_vals[i], p_vals[i-1]
        t_curr, t_prev = t_vals[i], t_vals[i-1]

        if np.isnan(t_curr) or np.isnan(t_prev):
            continue
            
        # Crossing Logic
        if p_curr > t_curr and p_prev <= t_prev:
            signals[i] = "BUY"
        elif p_curr < t_curr and p_prev >= t_prev:
            signals[i] = "SELL"
        else:
            signals[i] = "UP" if p_curr > t_curr else "DOWN"

    # Maintain compatibility with existing dashboard and entry script keys
    df['ST'] = df['TSMA_9']
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
        if DEBUG_MODE: print(f"TSMA Error: {e}")
        return "NONE", 0.0

if __name__ == "__main__":
    print(" TESTING TSMA 9 ENGINE ".center(50, "="))
    test_df = fetch_yf_data()
    if test_df is not None:
        df_full = calculate_supertrend(test_df)
        print(f"Latest Price: {test_df['Close'].iloc[-1]:.2f}")
        print(f"TSMA Line   : {df_full['ST'].iloc[-1]:.2f}")
        print(f"Trend State : {df_full['ST_Trend'].iloc[-1]}")
        print("-" * 50)
        print(df_full[['P_Master', 'ST', 'ST_Trend']].tail(5))




