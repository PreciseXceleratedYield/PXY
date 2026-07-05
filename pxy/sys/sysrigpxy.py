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

def calculate_linear_regression_channel(df: pd.DataFrame, length: int = 14, upper_mult: float = 2.0, lower_mult: float = 2.0) -> pd.DataFrame:
    """
    Translates TradingView Pine Script Linear Regression Channel calculations to Python.
    Features 100% mathematical synchronization with the Pine Script loop indexing.
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

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    df = df.tz_localize('UTC').tz_convert(tz_string) if df.index.tz is None else df.tz_convert(tz_string)

    # 1-to-1 Pine Loop Replication Setup (Chronological Reversal Mapping)
    source_vals = df['Close'].iloc[-length:].values[::-1] 
    high_vals = df['High'].iloc[-length:].values[::-1]
    low_vals = df['Low'].iloc[-length:].values[::-1]

    sumX = 0.0
    sumY = 0.0
    sumXSqr = 0.0
    sumXY = 0.0

    for i in range(length):
        val = source_vals[i]
        per = i + 1.0
        sumX += per
        sumY += val
        sumXSqr += per * per
        sumXY += val * per

    slope = (length * sumXY - sumX * sumY) / (length * sumXSqr - sumX * sumX)
    average = sumY / length
    intercept = average - slope * sumX / length + slope

    std_dev_acc = 0.0
    dsxx = 0.0
    dsyy = 0.0
    dsxy = 0.0
    periods = length - 1
    daY = intercept + slope * periods / 2.0
    
    val = intercept
    val_track = np.zeros(length)

    for j in range(length):
        val_track[j] = val
        dxt = source_vals[j] - average
        dyt = val - daY
        price_diff = source_vals[j] - val
        std_dev_acc += price_diff * price_diff
        dsxx += dxt * dxt
        dsyy += dyt * dyt
        dsxy += dxt * dyt
        val += slope

    divisor = 1.0 if periods == 0 else float(periods)
    std_dev = np.sqrt(std_dev_acc / divisor)
    pearson_r = 0.0 if (dsxx == 0 or dsyy == 0) else (dsxy / np.sqrt(dsxx * dsyy))

    # CRITICAL ORIENTATION FIX:
    # endPrice in Pine is intercept (Current Live Bar)
    # startPrice in Pine is intercept + slope * (length - 1) (Oldest Past Bar)
    start_price = intercept + slope * (length - 1)
    
    if intercept > start_price:
        trend_direction = "BULL"
    else:
        trend_direction = "BEAR"

    base_line_series = np.full(len(df), np.nan)
    upper_line_series = np.full(len(df), np.nan)
    lower_line_series = np.full(len(df), np.nan)

    base_line_series[-length:] = val_track[::-1]
    upper_line_series[-length:] = (val_track + (upper_mult * std_dev))[::-1]
    lower_line_series[-length:] = (val_track - (lower_mult * std_dev))[::-1]

    df['linreg_base'] = base_line_series
    df['linreg_upper'] = upper_line_series
    df['linreg_lower'] = lower_line_series
    df['sma_trend_full'] = trend_direction

    df['ST_Trend'] = df['sma_trend_full']
    df['ST'] = df['linreg_base'].ffill().fillna(0.0)

    df.attrs['pearson_r'] = pearson_r
    df.attrs['std_dev'] = std_dev
    df.attrs['slope'] = slope

    return df

def export_regression_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
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
    
    if processed_df is not None and not processed_df.empty and 'linreg_base' in processed_df.columns and not pd.isna(processed_df.iloc[-1]['linreg_base']):
        target_index = processed_df.index[-1]
        print(f"Timestamp    : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price  : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"LinReg Base  : {float(processed_df.at[target_index, 'linreg_base']):.2f}")
        print(f"LinReg Upper : {float(processed_df.at[target_index, 'linreg_upper']):.2f}")
        print(f"LinReg Lower : {float(processed_df.at[target_index, 'linreg_lower']):.2f}")
        print(f"Pearson's R  : {processed_df.attrs.get('pearson_r', 0.0):.6f}")
        print(f"Channel State: {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_regression_json(processed_df)
    else:
        print("CRITICAL: Upstream data error or insufficient data rows.")
