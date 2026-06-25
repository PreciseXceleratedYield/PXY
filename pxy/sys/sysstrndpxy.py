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
    """ Hybrid Pipeline: (SMA 42 + Live Close) / 2 Baseline Engine """
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

    src_close = df['Close'].to_numpy()

    # --- 1. Compute Base SMA 42 ---
    sma42_series = df['Close'].rolling(window=42).mean().bfill()
    sma42_arr = sma42_series.to_numpy()
    
    # --- 2. Blend with Live Close Price ---
    blended_line = (sma42_arr)
    df['pxy_sma_line'] = blended_line
    
    # Evaluate tracking direction relative to the blended baseline matrix
    blended_direction = np.where(src_close >= blended_line, 1, -1)

    # --- 3. Generate Regime Transition Switches ---
    sma_trend_history = []
    for i in range(n): 
        raw_sma_regime = "BULL" if blended_direction[i] == 1 else "BEAR"
        if i < 1: 
            sma_trend_history.append(raw_sma_regime)
            continue 

        sma_cross_buy  = (blended_direction[i] == 1)  and (blended_direction[i-1] == -1)
        sma_cross_sell = (blended_direction[i] == -1) and (blended_direction[i-1] == 1)

        if sma_cross_buy:
            sma_trend_history.append("BUY")
        elif sma_cross_sell:
            sma_trend_history.append("SELL")
        else:
            sma_trend_history.append(raw_sma_regime)

    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close
    
    # Backward compatibility mappings for dashboard integration
    df['pxy_st_line'] = df['pxy_sma_line']
    df['st_trend_full'] = df['sma_trend_full']
    df['ST'] = df['pxy_sma_line']
    df['ST_Trend'] = df['sma_trend_full']
    df['P_Master'] = df['src_c']
    
    try:
        df['shared_atr'] = calculate_atr(df)
    except Exception:
        df['shared_atr'] = 12.0
    
    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """ Dumps data framework directly to JSON file with legacy keys """
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
            "sma_trend": str(row["sma_trend_full"])
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY BLENDED (SMA42 + LIVE) / 2 MONITOR ENGINE ---")
    
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        idx_pos = -2 if CHECK_CONFIRMED_ONLY else -1
        target_index = processed_df.index[idx_pos]
        
        print(f"Target Row Index Position -> {idx_pos} ({'CLOSED BAR' if CHECK_CONFIRMED_ONLY else 'LIVE TICK'})")
        print(f"Timestamp    : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price  : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"Blended Line : {float(processed_df.at[target_index, 'pxy_sma_line']):.2f}")
        print(f"Trend State  : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")

