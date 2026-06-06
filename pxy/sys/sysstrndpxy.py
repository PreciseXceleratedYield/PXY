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
    PXY® Engine Strategy Matrix - Modular Dual-Pipeline Engine.
    Processes two completely separate, decoupled tracking streams:
    - Pipe A (Supertrend Matrix): 3:3 Trailing Band Crossovers
    - Pipe B (SMA Matrix)       : 42-Period Rolling Baseline Crossovers
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

    # EXTRACT UPSTREAM-TRANSFORMED DATA ARRAYS DIRECTLY
    src_high  = df['High'].to_numpy()
    src_low   = df['Low'].to_numpy()
    src_close = df['Close'].to_numpy()

    # ===============================================================================
    # 📡 PIPELINE A PROCESSING: NATIVE 3:3 SUPERTREND TRAILING LOCKS
    # ===============================================================================
    tr = np.zeros(n)
    for i in range(n):
        if i == 0:
            tr[i] = src_high[i] - src_low[i]
        else:
            tr1 = src_high[i] - src_low[i]
            tr2 = abs(src_high[i] - src_close[i-1])
            tr3 = abs(src_low[i] - src_close[i-1])
            tr[i] = max(tr1, tr2, tr3)

    atr = np.zeros(n)
    atr_period = 3        
    atr_multiplier = 3.0  
    
    if n >= atr_period:
        atr[atr_period - 1] = np.mean(tr[0:atr_period])
        for i in range(atr_period, n):
            atr[i] = (tr[i] + (atr_period - 1) * atr[i-1]) / atr_period
    else:
        atr = tr.copy()

    hl2 = (src_high + src_low) / 2.0
    up_band = hl2 - (atr_multiplier * atr)
    dn_band = hl2 + (atr_multiplier * atr)

    lower_band = np.zeros(n)
    upper_band = np.zeros(n)
    st_direction = np.ones(n, dtype=int)  # 1 = BULL, -1 = BEAR

    lower_band = up_band
    upper_band = dn_band

    for i in range(1, n):
        lower_band[i] = max(up_band[i], lower_band[i-1]) if src_close[i-1] > lower_band[i-1] else up_band[i]
        upper_band[i] = min(dn_band[i], upper_band[i-1]) if src_close[i-1] < upper_band[i-1] else dn_band[i]

        if st_direction[i-1] == 1:
            st_direction[i] = -1 if src_close[i] < lower_band[i] else 1
        else:
            st_direction[i] = 1 if src_close[i] > upper_band[i] else -1

    supertrend_line = np.where(st_direction == 1, lower_band, upper_band)
    df['pxy_st_line'] = supertrend_line

    # ===============================================================================
    # 📡 PIPELINE B PROCESSING: PURE 42 ROLLING SIMPLE MOVING AVERAGE
    # ===============================================================================
    sma_period = 42
    df['pxy_sma_line'] = df['Close'].rolling(window=sma_period, min_periods=1).mean()
    sma_line = df['pxy_sma_line'].to_numpy()

    sma_direction = np.ones(n, dtype=int)  # 1 = BULL, -1 = BEAR
    for i in range(n):
        if src_close[i] < sma_line[i]:
            sma_direction[i] = -1
        else:
            sma_direction[i] = 1

    # ===============================================================================
    # 🛠️ ISOLATED FIVE-STATE COUPLING AND VECTOR ARRAY GENERATION
    # ===============================================================================
    st_trend_history = []
    sma_trend_history = []
    
    for i in range(n): 
        # Base status parameters for the decoupled fallback states
        raw_st_regime = "BULL" if st_direction[i] == 1 else "BEAR"
        raw_sma_regime = "BULL" if sma_direction[i] == 1 else "BEAR"

        if i < 1: 
            st_trend_history.append(raw_st_regime)
            sma_trend_history.append(raw_sma_regime)
            continue 

        # --- PIPELINE A ARRAY GATING: PURE SUPERTREND SWITCHES ---
        st_cross_buy  = (st_direction[i] == 1)  and (st_direction[i-1] == -1)
        st_cross_sell = (st_direction[i] == -1) and (st_direction[i-1] == 1)

        if st_cross_buy:
            st_trend_history.append("BUY")
        elif st_cross_sell:
            st_trend_history.append("SELL")
        else:
            st_trend_history.append(raw_st_regime)

        # --- PIPELINE B ARRAY GATING: PURE 42 SMA SWITCHES ---
        sma_cross_buy  = (sma_direction[i] == 1)  and (sma_direction[i-1] == -1)
        sma_cross_sell = (sma_direction[i] == -1) and (sma_direction[i-1] == 1)

        if sma_cross_buy:
            sma_trend_history.append("BUY")
        elif sma_cross_sell:
            sma_trend_history.append("SELL")
        else:
            sma_trend_history.append(raw_sma_regime)

    # Save cleanly named vector columns into the calculation frame
    df['st_trend_full'] = st_trend_history
    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close
    
    # 🎯 DASHBOARD BACKWARD-COMPATIBILITY ROUTING KEYS
    df['ST'] = df['pxy_st_line']
    df['ST_Trend'] = df['st_trend_full']
    df['P_Master'] = df['src_c']
    
    # Append the session-grouped 14-period script calculations directly
    try:
        df['shared_atr'] = calculate_atr(df)
    except Exception:
        df['shared_atr'] = 12.0
    
    return df

def export_supertrend_json(output_file="../syschrtpxy.json"):
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
            "st": float(row["ST"]),           
            "st_trend": str(row["ST_Trend"]),
            "sma_line": float(row["pxy_sma_line"]),
            "sma_trend": str(row["sma_trend_full"])
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

def get_signal(df: pd.DataFrame) -> tuple:
    """Unpacks and returns Pipe A and Pipe B states cleanly for routing preferences."""
    if df is None or df.empty:
        df = pd.DataFrame()
        
    try:
        calculated_df = calculate_supertrend(df)
        n = len(calculated_df)
        if n == 0:
            return "NONE", "NONE"
        
        idx = n - 2 if CHECK_CONFIRMED_ONLY else n - 1  

        # Unpack the states completely decoupled from one another
        active_st_state  = str(calculated_df.at[calculated_df.index[idx], 'st_trend_full']).upper().strip()
        active_sma_state = str(calculated_df.at[calculated_df.index[idx], 'sma_trend_full']).upper().strip()
        
        latest_atr_val = int(calculated_df.at[calculated_df.index[idx], 'shared_atr'])
        latest_k_val = calculate_dynamic_k(calculated_df)

        if DEBUG_MODE:
            print(f"--- PXY DUAL-PIPE COUPLING SUMMARY ---")
            print(f"Target Row Lookup Index   -> {idx}")
            print(f"Pipe A (3:3 Supertrend)   -> {active_st_state}")
            print(f"Pipe B (42 Rolling SMA)   -> {active_sma_state}")
            print(f"Shared Engine Metrics     -> ATR: {latest_atr_val} | Dynamic K: {latest_k_val}\n")
            
        return active_st_state, active_sma_state
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Master Output Routing Module Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    dummy = pd.DataFrame()
    st_pipe, sma_pipe = get_signal(dummy)


