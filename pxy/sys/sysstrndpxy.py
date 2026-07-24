import os
import json
import numpy as np
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from sysdtafpxy import fetch_yf_data
from syscnfgpxy import TIMEZONE

DEBUG_MODE = False

def calculate_tsma_vectorized(series: pd.Series, window: int) -> pd.Series:
    """
    Calculates a 42-period Time Series Moving Average (Linear Regression Indicator).
    Uses a fast rolling window matrix operation for extreme precision.
    """
    if len(series) < window:
        return pd.Series(np.nan, index=series.index)
        
    # Pre-calculate linear regression constants for the lookback window
    x = np.arange(window)
    x_mean = x.mean()
    x_dev = x - x_mean
    x_var = (x_dev ** 2).sum()
    
    # Vectorized rolling linear regression forecast execution
    def get_lr_forecast(y_window):
        if len(y_window) < window:
            return np.nan
        y_mean = y_window.mean()
        slope = np.dot(x_dev, y_window - y_mean) / x_var
        intercept = y_mean - (slope * x_mean)
        return intercept + slope * (window - 1)

    # Apply rolling linear regression across the series
    return series.rolling(window=window, min_periods=window).apply(get_lr_forecast, raw=True)

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Implements a strict vectorized SMA + TSMA composite trend engine.
    Calculates a 42 SMA and a 42 TSMA, averages them to create the 'ST line'.
    Price above ST line = BULL | Price below ST line = BEAR.
    """
    try:
        raw_df = fetch_yf_data(period="3d", interval="1m")
        if raw_df is not None and not raw_df.empty:
            df = raw_df.copy()
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Shared pipeline download fallback active | {e}")
        df = df.copy()

    if df.empty:
        return df

    # Safe Datetime Index Normalisation
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    df = df.tz_convert(tz_string) if df.index.tz is not None else df.tz_localize('UTC').tz_convert(tz_string)

    # 1. Base Component Calculations (42 SMA and 42 TSMA)
    df['sma42'] = df['Close'].rolling(window=42, min_periods=1).mean()
    df['tsma42'] = calculate_tsma_vectorized(df['Close'], window=42)
    
    # Backfill early rows for TSMA to prevent downstream dashboard drops
    df['tsma42'] = df['tsma42'].fillna(df['sma42'])

    # 2. Combined Target Average Line (This is your ST Line)
    df['st_line'] = (df['sma42'] + df['tsma42']) / 2

    # DOWNSTREAM COMPATIBILITY ALIASES (Maps calculation directly to existing JSON keys)
    df['sma21'] = df['st_line']   # Keeps your dashboard charting the ST Line under the old label
    df['sma50'] = df['sma42']     # Keeps your dashboard charting the raw SMA 42 line under the old label
    df['ST'] = df['st_line']

    # 3. Direct Price Trend Verification Engine
    # Price ABOVE st_line is BULL | Price BELOW st_line is BEAR
    df['sma_trend_full'] = np.where(df['Close'] > df['st_line'], "BULL", "BEAR")
    df.loc[df['st_line'].isna(), 'sma_trend_full'] = "NONE"
    
    df['ST_Trend'] = df['sma_trend_full']

    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """
    Dumps clean structural data matrix to JSON matching your exact pipeline contracts.
    """
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
        if df is None or df.empty:
            return None

    output = []
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "sma21": float(row["sma21"]) if not pd.isna(row["sma21"]) else 0.0,   # ST Line value
            "sma50": float(row["sma50"]) if not pd.isna(row["sma50"]) else 0.0    # Pure SMA 42 Line value
        })

    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY UNIFIED EXCLUSIVE MATRIX ENGINE ---")
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        target_index = processed_df.index[-1]
        print(f"Timestamp   : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"O:{float(processed_df.at[target_index, 'Open']):.2f} H:{float(processed_df.at[target_index, 'High']):.2f} L:{float(processed_df.at[target_index, 'Low']):.2f} C:{float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"ST Line Value: {float(processed_df.at[target_index, 'sma21']):.2f} (SMA42 + TSMA42 Average)")
        print(f"SMA 42 Line  : {float(processed_df.at[target_index, 'sma50']):.2f}")
        print(f"Trend State  : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
