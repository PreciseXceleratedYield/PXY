# ===============================================================================
# SINGLE PIPELINE ENGINE: PURE JUMPING 42 SMA TRACKING ENGINE LINE ONLY
# ===============================================================================
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
CHECK_CONFIRMED_ONLY = True  # ⚡ True = Target the closed candle index (-2) | False = Target live running index (-1)

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    PXY® Engine Strategy Matrix - Unified Single-Pipeline Line Engine.
    Processes a single cohesive tracking line system over upstream Mode 0 candles:
    - Jumping 42 SMA Tracking Engine Line directly over upstream pricing inputs.
    Returns isolated categorical state flags to be matched downstream in the router.
    """ 
    # 🎯 OVERRIDE: Fetch historical day-session buffer block from data pipeline file if empty
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

    # EXTRACT UPSTREAM PRE-CALCULATED MODE 0 OHLC DATA ARRAYS
    src_open  = df['Open'].to_numpy()
    src_high  = df['High'].to_numpy()
    src_low   = df['Low'].to_numpy()
    src_close = df['Close'].to_numpy()

    # ===============================================================================
    # 📡 UNIFIED PIPELINE TRACK: JUMPING 42 SMA TRACKING ENGINE LINE
    # ===============================================================================
    sma_period = 42
    atr_length = 3
    atr_mult   = 3.0
    
    # Step A: Base rolling calculation (ta.sma)
    df['sma_baseline'] = df['Close'].rolling(window=sma_period, min_periods=1).mean()
    sma_baseline = df['sma_baseline'].to_numpy()
    
    # Step B: Compute continuous true range over upstream Mode 0 inputs
    tr_mod = np.zeros(n)
    tr_mod = src_high - src_low
    for i in range(1, n):
        t1 = src_high[i] - src_low[i]
        t2 = abs(src_high[i] - src_close[i-1])
        t3 = abs(src_low[i] - src_close[i-1])
        tr_mod[i] = max(t1, t2, t3)
        
    # Step C: Welles Wilder Smoothing matching Pine Script ta.atr() exactly
    atr_val = np.zeros(n)
    if n > 0:
        atr_val = tr_mod.copy()
        for i in range(1, n):
            # Pine RMA formula: (prev * (length - 1) + current) / length
            atr_val[i] = (atr_val[i-1] * (atr_length - 1) + tr_mod[i]) / atr_length

    basic_upper = sma_baseline + (atr_val * atr_mult)
    basic_lower = sma_baseline - (atr_val * atr_mult)

    final_upper     = np.zeros(n)
    final_lower     = np.zeros(n)
    trend_direction = np.ones(n, dtype=int) # 1 = BULL, -1 = BEAR

    # Initialize the first index bar memory cells
    final_upper[0] = basic_upper[0]
    final_lower[0] = basic_lower[0]
    trend_direction[0] = 1 if src_close[0] >= sma_baseline[0] else -1

    for i in range(1, n):
        # ---- UPPER TRAIL LOCK (Exact copy of Pine's ternary logic) ----
        # final_upper := ((basic_upper < final_upper or close > final_upper) ? basic_upper : final_upper)
        if (basic_upper[i] < final_upper[i-1]) or (src_close[i-1] > final_upper[i-1]):
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i-1]

        # ---- LOWER TRAIL LOCK (Exact copy of Pine's ternary logic) ----
        # final_lower := ((basic_lower > final_lower or close < final_lower) ? basic_lower : final_lower)
        if (basic_lower[i] > final_lower[i-1]) or (src_close[i-1] < final_lower[i-1]):
            final_lower[i] = basic_lower[i]
        else:
            final_lower[i] = final_lower[i-1]

        # ---- DIRECTION SWITCH GATE ----
        prev_dir = trend_direction[i-1]
        if prev_dir == 1 and src_close[i] < final_lower[i]:
            trend_direction[i] = -1
        elif prev_dir == -1 and src_close[i] > final_upper[i]:
            trend_direction[i] = 1
        else:
            trend_direction[i] = prev_dir

    jumping_supertrend = np.where(trend_direction == 1, final_lower, final_upper)
    df['pxy_sma_line'] = jumping_supertrend

    # ===============================================================================
    # 🛠️ UNIFIED SINGLE ASYMMETRIC TREND STATE GENERATION
    # ===============================================================================
    sma_trend_history = []
    
    for i in range(n): 
        raw_sma_regime = "BULL" if trend_direction[i] == 1 else "BEAR"

        if i < 1: 
            sma_trend_history.append(raw_sma_regime)
            continue 

        # --- PIPELINE GATING: JUMPING 42 SMA ENGINE SWITCHES ---
        sma_cross_buy  = (trend_direction[i] == 1)  and (trend_direction[i-1] == -1)
        sma_cross_sell = (trend_direction[i] == -1) and (trend_direction[i-1] == 1)

        if sma_cross_buy:
            sma_trend_history.append("BUY")
        elif sma_cross_sell:
            sma_trend_history.append("SELL")
        else:
            sma_trend_history.append(raw_sma_regime)

    # Save cleanly named vector columns into the calculation frame
    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close
    
    # 🎯 DASHBOARD BACKWARD-COMPATIBILITY ROUTING KEYS
    df['pxy_st_line'] = df['pxy_sma_line']
    df['st_trend_full'] = df['sma_trend_full']
    df['ST'] = df['pxy_sma_line']
    df['ST_Trend'] = df['sma_trend_full']
    df['P_Master'] = df['src_c']
    
    # Append the session-grouped 14-period script calculations directly
    try:
        df['shared_atr'] = calculate_atr(df)
    except Exception:
        df['shared_atr'] = 12.0
    
    return df

def export_supertrend_json(output_file="../web/webchrtpxy.json"):
    """Dumps EVERY single candle printed straight to the JSON file."""
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
    """Unpacks and returns the sole pipeline state cleanly for routing preferences."""
    if df is None or df.empty:
        df = pd.DataFrame()
        
    try:
        calculated_df = calculate_supertrend(df)
        n = len(calculated_df)
        if n == 0:
            return "NONE"
        
        idx = n - 2 if CHECK_CONFIRMED_ONLY else n - 1  

        # Unpack state from single pipeline setup
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
