# sysrtsmapxy.py
import os
import json
import numpy as np
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from sysdtafpxy import fetch_yf_data
from syscnfgpxy import TIMEZONE

DEBUG_MODE = False

def calculate_linear_regression_channel(df: pd.DataFrame, length: int = 9) -> pd.DataFrame:
    """
    Calculates a continuous rolling linear regression line across the entire dataset.
    Signals BULL when Close price is above the line, and BEAR when below the line.
    """
    try:
        if df is None or df.empty or 'Close' not in df.columns:
            raw_df = fetch_yf_data()
            if raw_df is not None and not raw_df.empty:
                df = raw_df.copy()
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Shared pipeline download fallback active | {e}")
            
    df = df.copy()

    # Pre-allocate columns with standard type formats
    df['linreg_base'] = np.nan
    df['sma_trend_full'] = "NONE"
    df['ST_Trend'] = "NONE"
    df['ST'] = 0.0
    df.attrs['slope'] = 0.0

    if df.empty or len(df) < length:
        return df

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    tz_string = str(TIMEZONE)
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(tz_string)
    else:
        df = df.tz_convert(tz_string)

    # --- VECTORIZED ROLLING LINEAR REGRESSION CORE ---
    x = np.arange(length)
    x_sum = x.sum()
    x_sum_sq = (x ** 2).sum()
    divisor = (length * x_sum_sq) - (x_sum ** 2)

    close_series = df['Close'].values
    rolling_bases = np.full(len(df), np.nan)
    rolling_slopes = np.full(len(df), 0.0)

    for i in range(length - 1, len(df)):
        y = close_series[i - length + 1 : i + 1]
        y_sum = y.sum()
        xy_sum = (x * y).sum()

        slope = (length * xy_sum - x_sum * y_sum) / divisor
        intercept = (y_sum - slope * x_sum) / length
        end_price = intercept + slope * (length - 1)

        rolling_bases[i] = end_price
        rolling_slopes[i] = slope

    df['linreg_base'] = rolling_bases

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

