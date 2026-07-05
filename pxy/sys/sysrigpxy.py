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

def calculate_linear_regression_channel(df: pd.DataFrame, length: int = 100, upper_mult: float = 2.0, lower_mult: float = 2.0) -> pd.DataFrame:
    """
    Translates TradingView Pine Script Linear Regression Channel calculations to Python.
    Uses the identical upstream data source context with zero parameter overrides.
    """
    try:
        raw_df = fetch_yf_data()
        if raw_df is not None and not raw_df.empty:
            df = raw_df.copy()
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Shared pipeline download fallback active | {e}")
        df = df.copy()

    if df.empty or len(df) < length:
        # Prevent silent failures down the line by initializing empty fallback columns if data is too short
        df['linreg_base'] = np.nan
        df['linreg_upper'] = np.nan
        df['linreg_lower'] = np.nan
        df['sma_trend_full'] = "NONE"
        df['ST_Trend'] = "NONE"
        df['ST'] = 0.0
        df.attrs['pearson_r'] = 0.0
        df.attrs['std_dev'] = 0.0
        df.attrs['slope'] = 0.0
        return df

    # Safe Datetime Index Normalisation
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    df = df.tz_localize('UTC').tz_convert(tz_string) if df.index.tz is None else df.tz_convert(tz_string)

    # Prepare calculation arrays for the most recent window slice (replicating barstate.islast logic)
    x_indices = np.arange(1, length + 1, dtype=float)
    y_values = df['Close'].iloc[-length:].values
    
    # Calculate Linear Regression variables matching calcSlope function exactly
    sumX = np.sum(x_indices)
    sumY = np.sum(y_values)
    sumXSqr = np.sum(x_indices ** 2)
    sumXY = np.sum(x_indices * y_values)
    
    slope = (length * sumXY - sumX * sumY) / (length * sumXSqr - sumX * sumX)
    average = sumY / length
    intercept = average - slope * sumX / length + slope
    
    # Replicating startPrice and endPrice calculations
    end_price = intercept
    start_price = intercept + slope * (length - 1)
    
    # Calculate Standard Deviation, Pearson's R, Max High Dev, and Max Low Dev matching calcDev function
    high_vals = df['High'].iloc[-length:].values
    low_vals = df['Low'].iloc[-length:].values
    source_vals = df['Close'].iloc[-length:].values
    
    periods = length - 1
    daY = intercept + slope * periods / 2
    
    # Generate the linear base regression array path across the lookback block
    val_track = intercept + slope * np.arange(length)
    
    # Find max absolute price distance points for fallback deviations
    up_dev_array = high_vals - val_track
    dn_dev_array = val_track - low_vals
    upDev = np.max(up_dev_array) if np.max(up_dev_array) > 0 else 0.0
    dnDev = np.max(dn_dev_array) if np.max(dn_dev_array) > 0 else 0.0
    
    # Calculated Pearson R matrices
    dxt = source_vals - average
    dyt = val_track - daY
    dsxx = np.sum(dxt * dxt)
    dsyy = np.sum(dyt * dyt)
    dsxy = np.sum(dxt * dyt)
    
    std_dev_acc = np.sum((source_vals - val_track) ** 2)
    std_dev = np.sqrt(std_dev_acc / (1 if periods == 0 else periods))
    pearson_r = 0.0 if (dsxx == 0 or dsyy == 0) else (dsxy / np.sqrt(dsxx * dsyy))
    
    # Calculate upper/lower band start and end values
    upper_start_price = start_price + (upper_mult * std_dev)
    upper_end_price = end_price + (upper_mult * std_dev)
    lower_start_price = start_price - (lower_mult * std_dev)
    lower_end_price = end_price - (lower_mult * std_dev)
    
    # Calculate trend metrics (Pine Script: float trend = math.sign(startPrice - endPrice))
    trend_val = np.sign(start_price - end_price)
    trend_direction = "BULL" if trend_val < 0 else "BEAR"
    
    # Back-fill channel values into the dataframe timeline strictly across the historical footprint
    base_line_series = np.full(len(df), np.nan)
    upper_line_series = np.full(len(df), np.nan)
    lower_line_series = np.full(len(df), np.nan)
    
    # Generate current array trend lines reversed to match chronological timeline index
    base_line_series[-length:] = val_track[::-1]
    upper_line_series[-length:] = (val_track + (upper_mult * std_dev))[::-1]
    lower_line_series[-length:] = (val_track - (lower_mult * std_dev))[::-1]
    
    df['linreg_base'] = base_line_series
    df['linreg_upper'] = upper_line_series
    df['linreg_lower'] = lower_line_series
    df['sma_trend_full'] = trend_direction
    
    # COMPATIBILITY ALIASES (Preserves downstream sysdashpxy.py tracking matrix hooks)
    df['ST_Trend'] = df['sma_trend_full']
    df['ST'] = df['linreg_base'].ffill().fillna(0.0)
    
    # Attach single-value metrics to df properties for execution accessibility
    df.attrs['pearson_r'] = pearson_r
    df.attrs['std_dev'] = std_dev
    df.attrs['slope'] = slope
    
    return df

def export_regression_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """
    Dumps clean structural data matrix to JSON matching legacy channel payload parameters.
    """
    if df is None or df.empty:
        df = calculate_linear_regression_channel(pd.DataFrame())
        if df is None or df.empty:
            return None

    output = []
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "price": float(row["Close"]),
            "sma21": float(row["linreg_base"]) if not pd.isna(row["linreg_base"]) else 0.0,
            "sma50": float(row["linreg_upper"]) if not pd.isna(row["linreg_upper"]) else 0.0
        })

    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY LINEAR REGRESSION RUNTIME MATRIX ENGINE ---")
    processed_df = calculate_linear_regression_channel(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        target_index = processed_df.index[-1]
        print(f"Timestamp    : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price  : {float(processed_df.at[target_index, 'Close']):.2f}")
        
        # Safe conditional print tracking to protect against short data frames
        if 'linreg_base' in processed_df.columns and not pd.isna(processed_df.at[target_index, 'linreg_base']):
            print(f"LinReg Base  : {float(processed_df.at[target_index, 'linreg_base']):.2f}")
            print(f"LinReg Upper : {float(processed_df.at[target_index, 'linreg_upper']):.2f}")
            print(f"LinReg Lower : {float(processed_df.at[target_index, 'linreg_lower']):.2f}")
            print(f"Pearson's R  : {processed_df.attrs.get('pearson_r', 0.0):.6f}")
            print(f"Channel State: {str(processed_df.at[target_index, 'sma_trend_full'])}")
        else:
            print("CRITICAL: Data slice length is less than requested channel calculation window (100).")
            
        export_regression_json(processed_df)
    else:
        print("CRITICAL: Upstream data completely empty.")

