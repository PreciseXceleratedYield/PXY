# sysrigpxy.py
import os 
import json 
import numpy as np 
import pandas as pd 
import warnings 
warnings.simplefilter(action='ignore', category=FutureWarning) 

from sysdtafpxy import fetch_yf_data 
from syscnfgpxy import TIMEZONE 

DEBUG_MODE = False 

def calculate_linear_regression_channel(df: pd.DataFrame, length: int = 30) -> pd.DataFrame:
    """
    Calculates a continuous rolling linear regression line across the entire dataset.
    Eliminates historical 0.0/NaN artifacts from exported JSON matrices.
    """
    try:
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

    # Slide window chronologically across the entire dataset timeline
    for i in range(length - 1, len(df)):
        y = close_series[i - length + 1 : i + 1]
        y_sum = y.sum()
        xy_sum = (x * y).sum()
        
        slope = (length * xy_sum - x_sum * y_sum) / divisor
        intercept = (y_sum - slope * x_sum) / length
        
        # end_price is the current value of the rolling regression tracking line
        end_price = intercept + slope * (length - 1)
        
        rolling_bases[i] = end_price
        rolling_slopes[i] = slope

    df['linreg_base'] = rolling_bases

    # --- VECTORIZED TREND CONFIGURATION LAYER ---
    df['sma_trend_full'] = np.where(rolling_slopes > 0, "BULL", np.where(rolling_slopes < 0, "BEAR", "NONE"))
    df.loc[df['linreg_base'].isna(), 'sma_trend_full'] = "NONE"

    # Synchronize internal dashboard aliases seamlessly
    df['ST_Trend'] = df['sma_trend_full']
    df['ST'] = df['linreg_base'].ffill().fillna(0.0)

    if not pd.isna(rolling_slopes[-1]):
        df.attrs['slope'] = float(rolling_slopes[-1])

    return df

if __name__ == "__main__":
    print("--- TESTING ROLLING RIG ENGINE ALONE ---")
    test_df = calculate_linear_regression_channel(pd.DataFrame())
    if not test_df.empty:
        print(f"Latest Calculated Base: {test_df['linreg_base'].iloc[-1]:.2f}")
        print(f"Latest Trend Output   : {test_df['sma_trend_full'].iloc[-1]}")

