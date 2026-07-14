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
    Translates TradingView Pine Script v6 Linear Regression Channel calculations to Python.
    Maintains 100% mathematical synchronization with ta.linreg slopes.
    """
    try:
        raw_df = fetch_yf_data()
        if raw_df is not None and not raw_df.empty:
            df = raw_df.copy()
    except Exception as e:
        if DEBUG_MODE: 
            print(f"Warning: Shared pipeline download fallback active | {e}")
        df = df.copy()

    # Safely pre-allocate system columns
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

    # Replicate TradingView's lookback context array mapping
    source_vals = df['Close'].iloc[-length:].values
    
    # Generate X coordinates matching chronological index steps
    x = np.arange(length)
    y = source_vals
    
    # Calculate Standard Least Squares Linear Regression
    slope, intercept = np.polyfit(x, y, 1)
    
    # Derive exact boundary points to replicate ta.linreg(source, length, 0)
    start_price = intercept                  
    end_price = intercept + slope * (length - 1)  

    # 100% Synchronized Pine Direction Gateway: isBullish = endPrice > startPrice
    trend_direction = "BULL" if end_price > start_price else "BEAR"

    # Generate base line arrays for the calculated lookback series window
    val_track = start_price + slope * np.arange(length)

    base_line_series = np.full(len(df), np.nan)
    base_line_series[-length:] = val_track

    df['linreg_base'] = base_line_series

    # Map state strictly onto the active execution tracking window
    channel_state = np.full(len(df), "NONE", dtype=object)
    
    # Populate the live trading signals over the focus windows
    channel_state[-length:] = trend_direction
    
    # Completely eliminate historical row artifacts outside execution focus window
    if len(channel_state) >= 2:
        channel_state[:-2] = "NONE"

    df['sma_trend_full'] = channel_state
    df['ST_Trend'] = df['sma_trend_full']
    df['ST'] = df['linreg_base'].ffill().fillna(0.0)

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
        print(f"Channel State: {str(processed_df.at[target_index, 'sma_trend_full'])}")
        
        export_regression_json(processed_df)
    else:
        print("CRITICAL: Upstream data error or insufficient data rows.")



