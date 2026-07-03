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
from syskatrpxy import calculate_atr, calculate_dynamic_k
from syscnfgpxy import TIMEZONE, TICKER

DEBUG_MODE = False 
CHECK_CONFIRMED_ONLY = False  

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ Pure SuperTrend Engine with Constant ATR (10.0) and Factor (1.0) on Pre-Transformed Data """
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

    # --- 1. Directly Read Already-Transformed Data Arrays ---
    src_close = df['Close'].to_numpy()
    src_high = df['High'].to_numpy()
    src_low = df['Low'].to_numpy()

    # --- 2. Fixed Parameter SuperTrend Setup ---
    atr_factor = 1.0
    custom_atr = 10.0 # Constant distance value

    hl2 = (src_high + src_low) / 2.0
    basic_ub = hl2 + (atr_factor * custom_atr) # Exactly hl2 + 10
    basic_lb = hl2 - (atr_factor * custom_atr) # Exactly hl2 - 10

    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    supertrend_line = np.zeros(n)
    trend = np.ones(n) 

    # --- 3. Memory Band-Locking Loop ---
    for i in range(n):
        if i == 0:
            final_ub[i] = basic_ub[i]
            final_lb[i] = basic_lb[i]
            supertrend_line[i] = final_ub[i] if src_close[i] <= final_ub[i] else final_lb[i]
            trend[i] = 1 if src_close[i] > supertrend_line[i] else -1
            continue

        # Mathematical Memory Lock on Upper Band 
        if basic_ub[i] < final_ub[i-1] or src_close[i-1] > final_ub[i-1]:
            final_ub[i] = basic_ub[i]
        else:
            final_ub[i] = final_ub[i-1]

        # Mathematical Memory Lock on Lower Band
        if basic_lb[i] > final_lb[i-1] or src_close[i-1] < final_lb[i-1]:
            final_lb[i] = basic_lb[i]
        else:
            final_lb[i] = final_lb[i-1]

        # Determine Vector Directions
        if trend[i-1] == 1:
            trend[i] = 1 if src_close[i] >= final_lb[i] else -1
        else:
            trend[i] = -1 if src_close[i] <= final_ub[i] else 1

        supertrend_line[i] = final_lb[i] if trend[i] == 1 else final_ub[i]

    # --- Generate Strict 4-State Structural Regime Matrix ---
    sma_trend_history = []
    for i in range(n): 
        if i < 1: 
            sma_trend_history.append("BULL" if trend[i] == 1 else "BEAR")
            continue 

        cross_buy  = (trend[i] == 1)  and (trend[i-1] == -1)
        cross_sell = (trend[i] == -1) and (trend[i-1] == 1)

        if cross_buy:
            sma_trend_history.append("BUY")
        elif cross_sell:
            sma_trend_history.append("SELL")
        else:
            sma_trend_history.append("BULL" if trend[i] == 1 else "BEAR")

    # --- Structural Injection Mappings ---
    df['exit'] = sma_trend_history
    df['pxy_sma_line'] = supertrend_line
    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close 
    
    df['pxy_st_line'] = df['pxy_sma_line']
    df['st_trend_full'] = df['sma_trend_full']
    df['ST'] = df['pxy_sma_line']
    df['ST_Trend'] = df['sma_trend_full']
    df['P_Master'] = df['src_c']
    
    df['shared_atr'] = custom_atr
    
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
            "p_master": float(row["src_c"]), 
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
    print("--- STARTING LIVE PXY FIXED ATR ENGINE (PRE-TRANSFORMED DATA) ---")
    
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        idx_pos = -2 if CHECK_CONFIRMED_ONLY else -1
        target_index = processed_df.index[idx_pos]
        
        print(f"Target Row Index Position -> {idx_pos} ({'CLOSED BAR' if CHECK_CONFIRMED_ONLY else 'LIVE TICK'})")
        print(f"Timestamp   : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"ST 10.0 Line: {float(processed_df.at[target_index, 'pxy_sma_line']):.2f}")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
