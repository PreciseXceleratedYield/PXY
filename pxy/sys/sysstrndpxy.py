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
    """ Pure SuperTrend (1, 3) Pipeline Engine mapped to Legacy Target Channel Keys """
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
    src_high = df['High'].to_numpy()
    src_low = df['Low'].to_numpy()

    # --- Compute ATR Length 1 Logic ---
    prev_close = np.roll(src_close, 1)
    prev_close[0] = src_close[0] # Edge protection boundary
    
    tr1 = src_high - src_low
    tr2 = np.abs(src_high - prev_close)
    tr3 = np.abs(src_low - prev_close)
    true_range = np.maximum(tr1, np.maximum(tr2, tr3))
    
    # ATR 1 is functionally identical to the single bar True Range array
    atr1 = pd.Series(true_range).rolling(window=1).mean().fillna(true_range).to_numpy()

    # --- True SuperTrend Dynamic Bands ---
    atr_factor = 3.0
    hl2 = (src_high + src_low) / 2.0
    basic_ub = hl2 + (atr_factor * atr1)
    basic_lb = hl2 - (atr_factor * atr1)

    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    supertrend_line = np.zeros(n)
    trend = np.ones(n) 

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

        # Capture precise crossover moments
        cross_buy  = (trend[i] == 1)  and (trend[i-1] == -1)
        cross_sell = (trend[i] == -1) and (trend[i-1] == 1)

        if cross_buy:
            sma_trend_history.append("BUY")
        elif cross_sell:
            sma_trend_history.append("SELL")
        else:
            # Persistent memory states for standard continuation bars
            sma_trend_history.append("BULL" if trend[i] == 1 else "BEAR")

    df['pxy_sma_line'] = supertrend_line
    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close
    
    # Backward compatibility mappings for downstream stability
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
    """ Dumps exact candle framework data matrix directly to JSON """
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
            "st": float(row["pxy_sma_line"]),       # SuperTrend Line
            "st_trend": str(row["sma_trend_full"]), # Strict 4-State Output
            "sma_line": float(row["pxy_sma_line"]), # Legacy Key Kept Alive
            "sma_trend": str(row["sma_trend_full"]) # Legacy Key Kept Alive
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY PURE SMA 42 MONITOR ENGINE ---")
    
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        idx_pos = -2 if CHECK_CONFIRMED_ONLY else -1
        target_index = processed_df.index[idx_pos]
        
        print(f"Target Row Index Position -> {idx_pos} ({'CLOSED BAR' if CHECK_CONFIRMED_ONLY else 'LIVE TICK'})")
        print(f"Timestamp   : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"SMA 42 Line : {float(processed_df.at[target_index, 'pxy_sma_line']):.2f}")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
