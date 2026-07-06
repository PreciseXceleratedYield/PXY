import os 
import json 
import numpy as np 
import pandas as pd 
import warnings 
warnings.simplefilter(action='ignore', category=FutureWarning) 

from sysdtafpxy import fetch_yf_data 
from syscnfgpxy import TIMEZONE 

DEBUG_MODE = False 

def calculate_linear_regression_channel(df: pd.DataFrame, length: int = 14, upper_mult: float = 1.4, lower_mult: float = 1.4) -> pd.DataFrame:
    """
    Translates TradingView Pine Script Linear Regression Channel calculations to Python.
    Filters buy/sell signals to evaluate only the past closed candle and running candle.
    """
    try:
        raw_df = fetch_yf_data()
        if raw_df is not None and not raw_df.empty:
            df = raw_df.copy()
    except Exception as e:
        if DEBUG_MODE: 
            print(f"Warning: Shared pipeline download fallback active | {e}")
        df = df.copy()

    # Pre-allocate output columns safely to handle early exits
    df['linreg_base'] = np.nan
    df['linreg_upper'] = np.nan
    df['linreg_lower'] = np.nan
    df['sma_trend_full'] = "NONE"
    df['ST_Trend'] = "NONE"
    df['ST'] = 0.0
    
    df.attrs['pearson_r'] = 0.0
    df.attrs['std_dev'] = 0.0
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

    # 1-to-1 Pine Loop Replication Setup (Chronological Reversal Mapping)
    source_vals = df['Close'].iloc[-length:].values[::-1]
    
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
    
    if dsxx == 0 or dsyy == 0:
        pearson_r = 0.0
    else:
        pearson_r = dsxy / np.sqrt(dsxx * dsyy)

    start_price = intercept + slope * (length - 1)
    trend_direction = "BULL" if intercept <= start_price else "BEAR"

    # Map calculations back to the active tracking window
    base_line_series = np.full(len(df), np.nan)
    upper_line_series = np.full(len(df), np.nan)
    lower_line_series = np.full(len(df), np.nan)

    base_line_series[-length:] = val_track[::-1]
    upper_line_series[-length:] = (val_track + (upper_mult * std_dev))[::-1]
    lower_line_series[-length:] = (val_track - (lower_mult * std_dev))[::-1]

    df['linreg_base'] = base_line_series
    df['linreg_upper'] = upper_line_series
    df['linreg_lower'] = lower_line_series

    # --- CHOSEN LOGIC: RUNNING AND PAST CLOSED CANDLE ONLY ---
    high_touches_upper = df['High'] >= df['linreg_upper']
    low_touches_lower = df['Low'] <= df['linreg_lower']

    # Rolling window of 2 captures only the running candle (t) and past closed candle (t-1)
    sell_signal = high_touches_upper.rolling(2, min_periods=1).max() == 1
    buy_signal = low_touches_lower.rolling(2, min_periods=1).max() == 1

    channel_state = np.where(sell_signal, "SELL", np.where(buy_signal, "BUY", trend_direction))
    
    # Strip flag artifacts from historical rows to isolate current execution states
    channel_state[:len(df) - length] = "NONE"
    if len(channel_state) >= 2:
        channel_state[:-2] = "NONE"

    df['sma_trend_full'] = channel_state
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
            "linreg_base": float(row["linreg_base"]) if not pd.isna(row["linreg_base"]) else 0.0,
            "linreg_upper": float(row["linreg_upper"]) if not pd.isna(row["linreg_upper"]) else 0.0,
            "linreg_lower": float(row["linreg_lower"]) if not pd.isna(row["linreg_lower"]) else 0.0,
            "signal": str(row["sma_trend_full"])
        })

    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
        
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY LINE BRACKET ENGAGEMENT ENGINE ---")
    processed_df = calculate_linear_regression_channel(pd.DataFrame())
    
    if (processed_df is not None and not processed_df.empty and 
        'linreg_base' in processed_df.columns and not pd.isna(processed_df.iloc[-1]['linreg_base'])):
        
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

