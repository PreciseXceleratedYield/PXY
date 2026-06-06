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
CHECK_CONFIRMED_ONLY = True  # ⚡ False = Process and trade the LIVE running candle (Index -1)

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    PXY® Engine Strategy Matrix - 3:3 Zero-Interaction Dual-Pipe Framework.
    Processes the transformed, multi-mode matrix incoming from upstream supply.
    - Pipe A (Signal): Upstream Candle Transformed Flips (BUY / SELL / BULL / BEAR / NONE)
    - Pipe B (Trend) : Pure 3:3 Supertrend Line (BUY / SELL / BULL / BEAR / NONE)
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

    # 2. EXTRACT UPSTREAM-TRANSFORMED DATA ARRAYS DIRECTLY
    src_open  = df['Open'].to_numpy()
    src_high  = df['High'].to_numpy()
    src_low   = df['Low'].to_numpy()
    src_close = df['Close'].to_numpy()

    # 3. TRUE RANGE & SMOOTHED ATR ENGINE (CALIBRATED TO 3-PERIOD)
    tr = np.zeros(n)
    for i in range(n):
        if i == 0:
            tr[i] = src_high[i] - src_low[i]
        else:
            tr1 = src_high[i] - src_low[i]
            tr2 = abs(src_high[i] - src_close[i-1])
            tr3 = abs(src_low[i] - src_close[i-1])
            tr[i] = max(tr1, tr2, tr3)

    # Replicate TradingView's ta.rma exactly using a 3-period rolling matrix window
    atr = np.zeros(n)
    atr_period = 3        
    atr_multiplier = 3.0  
    
    if n >= atr_period:
        atr[atr_period - 1] = np.mean(tr[0:atr_period])
        for i in range(atr_period, n):
            atr[i] = (tr[i] + (atr_period - 1) * atr[i-1]) / atr_period
    else:
        atr = tr.copy()

    # 4. SUPERTREND TRAILING LOCK IMPLEMENTATION
    hl2 = (src_high + src_low) / 2.0
    up_band = hl2 - (atr_multiplier * atr)
    dn_band = hl2 + (atr_multiplier * atr)

    lower_band = np.zeros(n)
    upper_band = np.zeros(n)
    trend_direction = np.ones(n, dtype=int)  # 1 = BULL, -1 = BEAR

    lower_band = up_band
    upper_band = dn_band

    for i in range(1, n):
        lower_band[i] = max(up_band[i], lower_band[i-1]) if src_close[i-1] > lower_band[i-1] else up_band[i]
        upper_band[i] = min(dn_band[i], upper_band[i-1]) if src_close[i-1] < upper_band[i-1] else dn_band[i]

        if trend_direction[i-1] == 1:
            trend_direction[i] = -1 if src_close[i] < lower_band[i] else 1
        else:
            trend_direction[i] = 1 if src_close[i] > upper_band[i] else -1

    supertrend_line = np.where(trend_direction == 1, lower_band, upper_band)
    
    df['pxy_st_line'] = supertrend_line
    df['bar_count_session'] = np.arange(1, n + 1)
    df['src_c'] = src_close
    
    # 5. ISOLATED FIVE-STATE DUAL PIPELINE CALCULATION LOOP
    st_signal_history = [] 
    st_trend_history = []
    
    for i in range(n): 
        raw_regime = "BULL" if trend_direction[i] == 1 else "BEAR"

        if i < 1: 
            st_signal_history.append("NONE") 
            st_trend_history.append(raw_regime)
            continue 

        # --- PIPE 1 ENGINE: MATCHING UPSTREAM CANDLE GATES ---
        is_anchor_green  = src_close[i-1] >= src_open[i-1]
        is_trigger_green = src_close[i] >= src_open[i]

        src_bull = is_anchor_green and is_trigger_green
        src_bear = (not is_anchor_green) and (not is_trigger_green)
        src_sell = is_anchor_green and (not is_trigger_green)
        src_buy  = (not is_anchor_green) and is_trigger_green

        if src_buy:
            st_signal_history.append("BUY")
        elif src_sell:
            st_signal_history.append("SELL")
        elif src_bull:
            st_signal_history.append("BULL")
        elif src_bear:
            st_signal_history.append("BEAR")
        else:
            st_signal_history.append("NONE")

        # --- PIPE 2 ENGINE: PURE 3:3 SUPERTREND GATES ---
        cross_buy  = (trend_direction[i] == 1)  and (trend_direction[i-1] == -1)
        cross_sell = (trend_direction[i] == -1) and (trend_direction[i-1] == 1)

        if cross_buy:
            st_trend_history.append("BUY")
        elif cross_sell:
            st_trend_history.append("SELL")
        elif trend_direction[i] == 1:
            st_trend_history.append("BULL")
        elif trend_direction[i] == -1:
            st_trend_history.append("BEAR")
        else:
            st_trend_history.append("NONE")

    df['st_signal_full'] = st_signal_history
    df['st_trend_full'] = st_trend_history
    
    # 🎯 DASHBOARD BACKWARD-COMPATIBILITY KEYS
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
            "st_trend": str(row["ST_Trend"])  
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

def get_signal(df: pd.DataFrame) -> tuple:
    """Direct array slice endpoint collector matching checkout preferences."""
    if df is None or df.empty:
        df = pd.DataFrame()
        
    try:
        calculated_df = calculate_supertrend(df)
        n = len(calculated_df)
        if n == 0:
            return "NONE", "NONE"
        
        idx = n - 2 if CHECK_CONFIRMED_ONLY else n - 1  

        active_signal = str(calculated_df.at[calculated_df.index[idx], 'st_signal_full']).upper().strip()
        active_trend  = str(calculated_df.at[calculated_df.index[idx], 'st_trend_full']).upper().strip()
        
        latest_atr_val = int(calculated_df.at[calculated_df.index[idx], 'shared_atr'])
        latest_k_val = calculate_dynamic_k(calculated_df)

        if DEBUG_MODE:
            print(f"--- PXY STRATEGY EVALUATION SUMMARY ---")
            print(f"Target Row Lookup Index   -> {idx}")
            print(f"Active Live Market SIGNAL  -> {active_signal}")
            print(f"Active Live Market TREND   -> {active_trend}")
            print(f"Shared Engine Metrics     -> ATR: {latest_atr_val} | Dynamic K: {latest_k_val}\n")
            
        return active_signal, active_trend
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Master Output Routing Module Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    dummy = pd.DataFrame()
    signal, trend = get_signal(dummy)

