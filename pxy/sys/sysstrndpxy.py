# sysstrndpxy.py
import sys
import numpy as np
import pandas as pd
import pytz
import json
import os
from datetime import datetime
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)

from sysdtafpxy import fetch_yf_data
from syscnfgpxy import TIMEZONE, TICKER

DEBUG_MODE = False 
CHECK_CONFIRMED_ONLY = False  

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    Implements a simplified single-average pipeline.
    Tracks a 9-period TSMA line, using its crossovers and price relative 
    positioning to define the regime matrix. Keeps downstream structures intact.
    """
    try:
        raw_df = fetch_yf_data(period="3d", interval="1m") 
        if not raw_df.empty:
            df = raw_df
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Shared pipeline download fallback active | {e}")

    df = df.copy()

    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    df = df.tz_localize('UTC').tz_convert(tz_string) if df.index.tz is None else df.tz_convert(tz_string)
        
    n = len(df)
    if n == 0:
        return df

    # --- Pine Script Inputs ---
    tsma_length = 9     

    # Read pricing array
    src_close = df['Close'].to_numpy()

    # Calculate 9-Period Time Series Moving Average (Linear Regression End Value)
    tsma9 = np.zeros(n)
    for i in range(n):
        window_size = min(tsma_length, i + 1)
        y = src_close[i - window_size + 1 : i + 1]
        x = np.arange(window_size)
        
        x_mean = x.mean()
        y_mean = y.mean()
        
        num = np.sum((x - x_mean) * (y - y_mean))
        den = np.sum((x - x_mean) ** 2)
        slope = num / den if den != 0 else 0.0
        intercept = y_mean - slope * x_mean
        
        tsma9[i] = slope * (window_size - 1) + intercept

    # --- Custom Matrix Logic (BUY / SELL / BULL / BEAR) ---
    custom_regime_history = []
    for i in range(n): 
        if i < 1: 
            if src_close[i] >= tsma9[i]:
                custom_regime_history.append("BULL")
            else:
                custom_regime_history.append("BEAR")
            continue 

        # Crossover checks for live price crossing TSMA 9
        cross_buy  = (src_close[i] > tsma9[i]) and (src_close[i-1] <= tsma9[i-1])
        cross_sell = (src_close[i] < tsma9[i]) and (src_close[i-1] >= tsma9[i-1])

        if cross_buy:
            custom_regime_history.append("BUY")
        elif cross_sell:
            custom_regime_history.append("SELL")
        elif src_close[i] >= tsma9[i]:
            custom_regime_history.append("BULL")
        else:
            custom_regime_history.append("BEAR")

    # --- Direct Injection Pipeline to Match JSON UI Server Layout Exactly ---
    # We assign tsma9 to pxy_sma_line so downstream json mapping finds it seamlessly
    df['exit'] = custom_regime_history
    df['pxy_sma_line'] = tsma9       
    df['sma_trend_full'] = custom_regime_history
    df['src_c'] = src_close 
    
    df['pxy_st_line'] = df['pxy_sma_line']
    df['st_trend_full'] = df['sma_trend_full']
    df['ST'] = df['pxy_sma_line']
    df['ST_Trend'] = df['sma_trend_full']
    df['P_Master'] = df['src_c']
    df['shared_atr'] = np.zeros(n) # Placeholder to preserve structure without calculation overhead
    
    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """ Dumps exact candle framework data matrix directly to JSON with exit fields """
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
    
    if df is None or df.empty:
        return None

    output = []
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "close": float(row["Close"]),
            "p_master": float(row["Close"]),  
            "st": float(row["pxy_sma_line"]),       
            "st_trend": str(row["sma_trend_full"]), 
            "sma_line": float(row["pxy_sma_line"]), 
            "sma_trend": str(row["sma_trend_full"]),
            "exit": str(row["sma_trend_full"])       
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY UNIFIED TSMA9 ONLY ENGINE ---")
    
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        idx_pos = -2 if CHECK_CONFIRMED_ONLY else -1
        target_index = processed_df.index[idx_pos]
        
        print(f"Target Row Index Position -> {idx_pos} ({'CLOSED BAR' if CHECK_CONFIRMED_ONLY else 'LIVE TICK'})")
        print(f"Timestamp   : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"TSMA Line Matrix Value     : {float(processed_df.at[target_index, 'pxy_sma_line']):.2f}")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")


