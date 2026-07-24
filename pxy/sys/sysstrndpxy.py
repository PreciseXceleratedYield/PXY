import os
import json
import numpy as np
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from sysdtafpxy import fetch_yf_data
from syscnfgpxy import TIMEZONE

DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Implements a strict vectorized pure Supertrend engine (Period 3, Multiplier 1.5).
    Multiplier factor is cut exactly in half (3.0 / 2 = 1.5) to reduce jump distance.
    Duplicates the Supertrend calculation across both downstream tracker slots.
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

    # 1. Pure Supertrend Engine (Period 3, Multiplier 1.5)
    atr_period = 3
    atr_multiplier = 2  # Jump factor cut in half (3.0 / 2)
    
    # Calculate ATR components
    high_low = df['High'] - df['Low']
    high_close = (df['High'] - df['Close'].shift(1)).abs()
    low_close = (df['Low'] - df['Close'].shift(1)).abs()
    
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period, min_periods=1).mean()
    
    hl2 = (df['High'] + df['Low']) / 2
    basic_ub = hl2 + (atr_multiplier * atr)
    basic_lb = hl2 - (atr_multiplier * atr)
    
    # Initialize arrays for fast sequential execution loop
    final_ub = np.zeros(len(df))
    final_lb = np.zeros(len(df))
    supertrend_values = np.zeros(len(df))
    
    close_arr = df['Close'].values
    bub_arr = basic_ub.values
    blb_arr = basic_lb.values
    
    for i in range(len(df)):
        if i == 0:
            final_ub[i] = bub_arr[i]
            final_lb[i] = blb_arr[i]
            supertrend_values[i] = bub_arr[i]
        else:
            # Upper Band logic
            if bub_arr[i] < final_ub[i-1] or close_arr[i-1] > final_ub[i-1]:
                final_ub[i] = bub_arr[i]
            else:
                final_ub[i] = final_ub[i-1]
                
            # Lower Band logic
            if blb_arr[i] > final_lb[i-1] or close_arr[i-1] < final_lb[i-1]:
                final_lb[i] = blb_arr[i]
            else:
                final_lb[i] = final_lb[i-1]
                
            # Trend Assignment logic
            if supertrend_values[i-1] == final_ub[i-1]:
                supertrend_values[i] = final_ub[i] if close_arr[i] <= final_ub[i] else final_lb[i]
            else:
                supertrend_values[i] = final_lb[i] if close_arr[i] >= final_lb[i] else final_ub[i]

    # Establish main ST Line
    df['st_line'] = supertrend_values

    # DOWNSTREAM COMPATIBILITY ALIASES (Duplicates Supertrend into both legacy tracking keys)
    df['sma21'] = df['st_line']   # Maps Supertrend to the first JSON placeholder
    df['sma50'] = df['st_line']   # Maps Supertrend to the second JSON placeholder
    df['ST'] = df['st_line']

    # 2. Direct Price Trend Verification Engine
    df['sma_trend_full'] = np.where(df['Close'] > df['st_line'], "BULL", "BEAR")
    df.loc[df['st_line'].isna(), 'sma_trend_full'] = "NONE"
    
    df['ST_Trend'] = df['sma_trend_full']

    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
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
            "sma21": float(row["sma21"]) if not pd.isna(row["sma21"]) else 0.0,   # Supertrend 3, 1.5 value
            "sma50": float(row["sma50"]) if not pd.isna(row["sma50"]) else 0.0    # Duplicate Supertrend value
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
        print(f"ST Line Value: {float(processed_df.at[target_index, 'sma21']):.2f} (Pure Supertrend 3, 1.5)")
        print(f"Trend State  : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
