# systsmapxy.py
import numpy as np
import pandas as pd
from sysdtafpxy import fetch_yf_data

def getsystsmapxy(df: pd.DataFrame = None, length: int = 7) -> pd.DataFrame:
    """
    Calculates 7-period Close TSMA (Linear Regression Endpoint) using fast vectorized windows,
    averages it with raw Close, and identifies BULL/BEAR by comparing current to previous value.
    """
    if df is None or df.empty or 'Close' not in df.columns:
        df = fetch_yf_data()
        if df is None or df.empty:
            return pd.DataFrame()
            
    df = df.copy()
    if len(df) < length:
        return df

    # --- VECTORIZED TIME SERIES MOVING AVERAGE (TSMA 7) ---
    x = np.arange(length)
    x_mean = x.mean()
    x_deviations = x - x_mean
    variance_x = (x_deviations ** 2).sum()

    # Calculate rolling slopes and intercepts over the 7-period Close window
    rolling_close = df['Close'].rolling(window=length)
    slope = rolling_close.apply(lambda y: np.dot(y - y.mean(), x_deviations) / variance_x, raw=True)
    intercept = rolling_close.mean() - slope * x_mean
    
    # TSMA Endpoint formula: slope * (length - 1) + intercept
    tsma_close = slope * (length - 1) + intercept

    # --- APPLY MATHEMATICAL AVERAGE ENGINE ---
    df['final_close'] = (tsma_close + df['Close']) / 2.0

    # --- TREND EVALUATION: CURRENT VS PREVIOUS RUNNING AVERAGE ---
    df['sma_trend_full'] = np.where(df['final_close'] > df['final_close'].shift(1), "BULL", 
                           np.where(df['final_close'] < df['final_close'].shift(1), "BEAR", "NONE"))
    
    df.loc[df['final_close'].isna() | df['final_close'].shift(1).isna(), 'sma_trend_full'] = "NONE"

    # --- AUTOMATIC TERMINAL PRINT ENGAGEMENT LAYER ---
    latest_val = float(df['final_close'].iloc[-1])
    latest_state = str(df['sma_trend_full'].iloc[-1])

    color_code = "\033[92m" if latest_state == "BULL" else "\033[91m" if latest_state == "BEAR" else "\033[93m"
    print(f"{color_code}{f' {latest_state} <{latest_val:.2f}> ' :~^42}\033[0m")

    return df

if __name__ == "__main__":
    getsystsmapxy()

