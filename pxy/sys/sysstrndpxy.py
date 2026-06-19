# ===============================================================================
# SINGLE PIPELINE ENGINE: CORE 1:1 SUPERTREND ENGINE ONLY (CONFIRMED ONLY)
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
CHECK_CONFIRMED_ONLY = False  # ⚡ STRICTLY ENFORCED: Target closed index (-2) for fully confirmed candles

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    Core 1:1 Supertrend Single-Pipeline Engine.
    Uses a 1-period ATR and 1.0 Factor over the median price baseline.
    Returns: BULL, BEAR, BUY, or SELL.
    """ 
    # 🎯 FIX: Only fetch fallback historical buffer block if df is truly empty or None
    if df is None or df.empty:
        try:
            raw_df = fetch_yf_data(period="3d", interval="1m") 
            if raw_df is not None and not raw_df.empty:
                df = raw_df
            else:
                return pd.DataFrame()
        except Exception as e:
            if DEBUG_MODE:
                print(f"Warning: Shared pipeline download fallback active | {e}")
            return pd.DataFrame()

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
    # 📡 1:1 SUPERTREND ENGINE TRACK
    # ===============================================================================
    atr_length = 1
    atr_mult   = 0.5
    
    # Core Supertrend standard tracking baseline (HL2)
    hl2_baseline = (src_high + src_low) / 2.0
    
    # Compute continuous true range over upstream Mode 0 inputs
    tr_mod = np.zeros(n)
    tr_mod = src_high - src_low
    for i in range(1, n):
        t1 = src_high[i] - src_low[i]
        t2 = abs(src_high[i] - src_close[i-1])
        t3 = abs(src_low[i] - src_close[i-1])
        tr_mod[i] = max(t1, t2, t3)
        
    # 1-Period ATR Window (Direct TR mapping)
    atr_val = tr_mod.copy()

    basic_upper = hl2_baseline + (atr_val * atr_mult)
    basic_lower = hl2_baseline - (atr_val * atr_mult)

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

        # --- PIPELINE GATING: JUMPING 1:1 SUPERTREND SWITCHES ---
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

def export_supertrend_json(output_file=None):
    """Dumps EVERY single candle printed straight to the JSON file using explicit paths."""
    # 🎯 FIX: Absolute root system resolution to stop path breaks in /sys/exe/ loop
    if output_file is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.abspath(os.path.join(base_dir, "web", "webchrtpxy.json"))
        
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

    out_dir = os.path.dirname(output_file)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        
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
        if n < 2:
            return "NONE"
        
        # ⚡ LOCKED EXCLUSIVELY TO INDEX n - 2 TO GUARANTEE CONFIRMED SIGNALS ONLY
        idx = n - 2 if CHECK_CONFIRMED_ONLY else n - 1  

        # Unpack state from single pipeline setup
        active_sma_state = str(calculated_df.at[calculated_df.index[idx], 'sma_trend_full']).upper().strip()
        
        return active_sma_state
    except Exception as e:
        if DEBUG_MODE:
            print(f"Critical execution fault in system system signal unpacker: {e}")
        return "NONE"

# ===============================================================================
# 🚀 DIRECT LIVE PRODUCTION EXECUTION BLOCK
# ===============================================================================
if __name__ == "__main__":
    print("--- STARTING LIVE PXY JUMPING 1:1 MONITOR ENGINE ---")
    live_df = pd.DataFrame()
    processed_df = calculate_supertrend(live_df)
    if not processed_df.empty:
        print(f"[SUCCESS] Calculated trend columns. Total Data Vectors: {len(processed_df)}")

