# sysrtsmapxy.py
import numpy as np
import pandas as pd
from sysdtafpxy import fetch_yf_data

def calculate_linear_regression_channel(df: pd.DataFrame, length: int = 9) -> pd.DataFrame:
    """
    Calculates 9-period Close TSMA average with raw Close.
    Defines and prints BULL/BEAR by comparing current average to previous average.
    """
    if df is None or df.empty or 'Close' not in df.columns:
        df = fetch_yf_data()
        if df is None or df.empty:
            return pd.DataFrame()
            
    df = df.copy()
    if len(df) < length:
        return df

    # --- VECTORIZED ROLLING LINEAR REGRESSION FOR CLOSE ---
    x = np.arange(length)
    x_sum = x.sum()
    x_sum_sq = (x ** 2).sum()
    divisor = (length * x_sum_sq) - (x_sum ** 2)

    raw_c = df['Close'].values
    f_close = np.full(len(df), np.nan)

    for i in range(length - 1, len(df)):
        y_c = raw_c[i - length + 1 : i + 1]

        slope_c = (length * (x * y_c).sum() - x_sum * y_c.sum()) / divisor
        tsma_c = ((y_c.sum() - slope_c * x_sum) / length) + slope_c * (length - 1)
        f_close[i] = (tsma_c + raw_c[i]) / 2.0

    df['final_close'] = f_close

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
    calculate_linear_regression_channel(pd.DataFrame())

    # --- VECTORIZED TREND CONFIGURATION LAYER (PRICE VS LINE) ---
    # BULL if Close > Linear Regression line; BEAR if Close < Linear Regression line
    df['sma_trend_full'] = np.where(df['Close'] > df['linreg_base'], "BULL", 
                           np.where(df['Close'] < df['linreg_base'], "BEAR", "NONE"))
    
    df.loc[df['linreg_base'].isna(), 'sma_trend_full'] = "NONE"

    # Synchronize internal dashboard aliases seamlessly
    df['ST_Trend'] = df['sma_trend_full']
    df['ST'] = df['linreg_base'].ffill().fillna(0.0)

    if not pd.isna(rolling_slopes[-1]):
        df.attrs['slope'] = float(rolling_slopes[-1])

    # --- AUTOMATIC TERMINAL PRINT ENGAGEMENT LAYER ---
    latest_val = float(df['linreg_base'].iloc[-1])
    latest_state = str(df['sma_trend_full'].iloc[-1])

    color_code = "\033[92m" if latest_state == "BULL" else "\033[91m" if latest_state == "BEAR" else "\033[93m"
    reset_code = "\033[0m"
    
    text_content = f" {latest_state} <{latest_val:.2f}> "
    status_bar = text_content.center(42, "~")
    
    print(f"{color_code}{status_bar}{reset_code}")

    return df

if __name__ == "__main__":
    calculate_linear_regression_channel(pd.DataFrame())
