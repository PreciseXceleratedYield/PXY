# ===============================================================================
# SINGLE PIPELINE ENGINE: DYNAMIC SUPERTREND ENGINE ONLY (ROUNDED 14-ATR PARAM)
# ===============================================================================
# sysatrndpxy.py
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

def calculate_atrnd_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    Core Dynamic Supertrend Single-Pipeline Engine.
    Calculates a standard baseline 14-period ATR, rounds it, and then dynamically 
    uses that rounded value as the active period and factor for the Supertrend.
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

    # Core Supertrend standard tracking baseline (HL2)
    hl2_baseline = (src_high + src_low) / 2.0
    
    # Compute continuous true range over upstream Mode 0 inputs
    tr_mod = np.zeros(n)
    if n > 0:
        tr_mod = src_high - src_low
    for i in range(1, n):
        t1 = src_high[i] - src_low[i]
        t2 = abs(src_high[i] - src_close[i-1])
        t3 = abs(src_low[i] - src_close[i-1])
        tr_mod[i] = max(t1, t2, t3)
        
    # Step 1: Compute baseline 14-period ATR (Wilder's RMA Standard)
    base_length = 14
    atr_base = np.zeros(n)
    if n >= base_length:
        atr_base[base_length-1] = np.mean(tr_mod[:base_length])
        for i in range(base_length, n):
            atr_base[i] = (atr_val_temp := (atr_base[i-1] * (base_length - 1) + tr_mod[i]) / base_length)
    else:
        atr_base = tr_mod.copy()

    # Step 2: Get rounded ATR values to use directly as the factor multiplier
    dynamic_factor = np.round(atr_base, 2)

    # Step 3: Use the rounded 14-ATR as a dynamic rolling period window
    atr_val = np.zeros(n)
    for i in range(n):
        # Cast the dynamic factor to an integer for lookback slicing
        # Safety floor of 1 protects against empty arrays on extremely tight instruments
        dyn_len = max(1, int(np.round(dynamic_factor[i])))
        
        if i >= dyn_len - 1:
            # Re-smooth window across the dynamically sized lookback slice
            tr_slice = tr_mod[max(0, i - dyn_len + 1):i + 1]
            atr_val[i] = np.mean(tr_slice)
        else:
            atr_val[i] = tr_mod[i]

    # Post-process security rounding on the finalized dynamic ATR array
    atr_val = np.round(atr_val, 2)

    # ===============================================================================
    # 📡 DYNAMIC SUPERTREND ENGINE TRACK (14-ATR BASELINE GENERATED)
    # ===============================================================================
    basic_upper = hl2_baseline + (atr_val * dynamic_factor)
    basic_lower = hl2_baseline - (atr_val * dynamic_factor)

    final_upper     = np.zeros(n)
    final_lower     = np.zeros(n)
    trend_direction = np.ones(n, dtype=int) # 1 = BULL, -1 = BEAR

    # Initialize the first index bar memory cells Safely across Vector
    final_upper = basic_upper.copy()
    final_lower = basic_lower.copy()
    trend_direction = np.where(src_close >= hl2_baseline, 1, -1)

    for i in range(1, n):
        # ---- UPPER TRAIL LOCK ----
        if (basic_upper[i] < final_upper[i-1]) or (src_close[i-1] > final_upper[i-1]):
            final_upper[i] = basic_upper[i]
        else:
            final_upper[i] = final_upper[i-1]

        # ---- LOWER TRAIL LOCK ----
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

        # --- PIPELINE GATING: JUMPING SUPERTREND SWITCHES ---
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

def export_atrnd_supertrend_json(output_file="../web/webchrtpxy.json"):
    """Dumps EVERY single candle printed straight to the JSON file."""
    dummy_df = pd.DataFrame()
    df = calculate_atrnd_supertrend(dummy_df)
    
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

def get_atrnd_signal(df: pd.DataFrame) -> str:
    """Unpacks and returns the sole pipeline state cleanly for routing preferences."""
    if df is None or df.empty:
        df = pd.DataFrame()
        
    try:
        calculated_df = calculate_atrnd_supertrend(df)
        n = len(calculated_df)
        if n == 0:
            return "NONE"
        
        idx = n - 2 if CHECK_CONFIRMED_ONLY else n - 1  

        # Unpack state from single pipeline setup
        active_sma_state = str(calculated_df.at[calculated_df.index[idx], 'sma_trend_full']).upper().strip()
        
        latest_atr_val = int(calculated_df.at[calculated_df.index[idx], 'shared_atr'])
        latest_k_val = calculate_dynamic_k(calculated_df)

        if DEBUG_MODE:
            print(f"--- ATRND SINGLE-PIPE MONITOR SUMMARY ---")
            print(f"Target Row Lookup Index   -> {idx}")
            print(f"Active Trend state        -> {active_sma_state}")
            
        return active_sma_state
    except Exception as e:
        if DEBUG_MODE:
            print(f"Critical execution fault in system signal unpacker: {e}")
        return "NONE"
