# sysstrndpxy.py
import sys
import numpy as np
import pandas as pd
import pytz
import json
import os
from datetime import datetime
import warnings

# Silence future warning constraints completely
warnings.simplefilter(action='ignore', category=FutureWarning)

# ---- Pure Production Naming Alignment Imports ----
from sysdtafpxy import fetch_yf_data
from syskatrpxy import calculate_atr, calculate_dynamic_k
from syscnfgpxy import TIMEZONE, TICKER

# Global Config 
DEBUG_MODE = False 
CHECK_CONFIRMED_ONLY = False  # ⚡ False = Target live running index (-1) for real-time changes

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    Pure SMA 50 Pipeline Engine. (Supertrend Logic Completely Removed)
    Tracks price position relative to a 50-period Simple Moving Average.
    Returns: BULL, BEAR, BUY, or SELL based on the SMA 50 crossover status.
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
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(tz_string)
    else:
        df = df.tz_convert(tz_string)
        
    n = len(df)
    if n == 0:
        return df

    # EXTRACT UPSTREAM CLOSE DATA ARRAYS
    src_close = df['Close'].to_numpy()

    # ===============================================================================
    # 📈 COMPUTE PURE SMA 50 PIPELINE TRACK
    # ===============================================================================
    sma50_series = df['Close'].rolling(window=50).mean()
    sma50_series = sma50_series.bfill()
    sma50_arr = sma50_series.to_numpy()
    
    df['pxy_sma_line'] = sma50_arr

    # Determine trend states relative to SMA 50 line
    sma_direction = np.ones(n, dtype=int)
    sma_direction = np.where(src_close >= sma50_arr, 1, -1)

    # ===============================================================================
    # 🛠️ UNIFIED SINGLE ASYMMETRIC TREND STATE GENERATION
    # ===============================================================================
    sma_trend_history = []
    
    for i in range(n): 
        raw_sma_regime = "BULL" if sma_direction[i] == 1 else "BEAR"

        if i < 1: 
            sma_trend_history.append(raw_sma_regime)
            continue 

        # --- PIPELINE GATING: SMA 50 CROSSOVER SWITCHES ---
        sma_cross_buy  = (sma_direction[i] == 1)  and (sma_direction[i-1] == -1)
        sma_cross_sell = (sma_direction[i] == -1) and (sma_direction[i-1] == 1)

        if sma_cross_buy:
            sma_trend_history.append("BUY")
        elif sma_cross_sell:
            sma_trend_history.append("SELL")
        else:
            sma_trend_history.append(raw_sma_regime)

    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close
    
    # 🎯 DASHBOARD BACKWARD-COMPATIBILITY ROUTING KEYS (Preserved layout layout channels)
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
    """Dumps EVERY single candle printed straight to the JSON file using SMA 50 parameters."""
    if df is None or df.empty:
        dummy_df = pd.DataFrame()
        df = calculate_supertrend(dummy_df)
    
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

def get_signal(df: pd.DataFrame) -> str:
    """Unpacks and returns the SMA 50 pipeline state cleanly for routing preferences."""
    if df is None or df.empty:
        df = pd.DataFrame()
        
    try:
        calculated_df = calculate_supertrend(df)
        n = len(calculated_df)
        if n == 0:
            return "NONE"
        
        idx = n - 2 if CHECK_CONFIRMED_ONLY else n - 1  
        active_sma_state = str(calculated_df.at[calculated_df.index[idx], 'sma_trend_full']).upper().strip()
        
        latest_atr_val = int(calculated_df.at[calculated_df.index[idx], 'shared_atr'])
        latest_k_val = calculate_dynamic_k(calculated_df)

        if DEBUG_MODE:
            print(f"--- PXY SINGLE-PIPE MONITOR SUMMARY ---")
            print(f"Target Row Lookup Index   -> {idx}")
            print(f"Active Trend state        -> {active_sma_state}")
            
        return active_sma_state
    except Exception as e:
        if DEBUG_MODE:
            print(f"Critical execution fault in system signal unpacker: {e}")
        return "NONE"

# ===============================================================================
# 🚀 DIRECT LIVE PRODUCTION EXECUTION BLOCK
# ===============================================================================
if __name__ == "__main__":
    print("--- STARTING LIVE PXY PURE SMA 50 MONITOR ENGINE ---")
    
    live_df = pd.DataFrame()
    processed_df = calculate_supertrend(live_df)
    
    if processed_df is not None and not processed_df.empty:
        idx_pos = -2 if CHECK_CONFIRMED_ONLY else -1
        target_index = processed_df.index[idx_pos]
        
        live_time = target_index.strftime('%Y-%m-%d %H:%M:%S %Z')
        live_close = float(processed_df.at[target_index, 'Close'])
        live_line = float(processed_df.at[target_index, 'pxy_sma_line'])
        live_state = str(processed_df.at[target_index, 'sma_trend_full'])
        
        print(f"Target Row Index Position -> {idx_pos} ({'CLOSED BAR' if CHECK_CONFIRMED_ONLY else 'LIVE TICK'})")
        print(f"Timestamp   : {live_time}")
        print(f"Close Price : {live_close:.2f}")
        print(f"SMA 50 Line : {live_line:.2f}")
        print(f"Trend State : {live_state}")
        
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Engine calculation aborted | Upstream data stream arrived empty.")



