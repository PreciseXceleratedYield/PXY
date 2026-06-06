# sysstrndpxy.py
import sys
import numpy as np
import pandas as pd
import pytz
import yfinance as yf
import json
import os
from datetime import datetime

# 🛠️ GLOBAL PROJECT HOTPATCH: Overrides config objects at initialization to prevent yfinance/pytz crashes
try:
    import syscnfgpxy
    if hasattr(syscnfgpxy, 'TIMEZONE'):
        if hasattr(syscnfgpxy.TIMEZONE, 'zone'):
            syscnfgpxy.TIMEZONE = str(syscnfgpxy.TIMEZONE.zone)
        else:
            syscnfgpxy.TIMEZONE = str(syscnfgpxy.TIMEZONE)
except Exception:
    pass

from syscnfgpxy import TIMEZONE, TICKER

# Global Config 
DEBUG_MODE = True 
CHECK_CONFIRMED_ONLY = False  # ⚡ False = Process and trade the LIVE running candle (Index -1)

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    PXY® Engine Strategy Matrix - Perfect 5-State Zero-Interaction Dual-Pipe Indicator Framework.
    - Pipe A (Signal): Pure Heikin-Ashi (BUY / SELL / BULL / BEAR / NONE)
    - Pipe B (Trend) : Pure Supertrend Line (BUY / SELL / BULL / BEAR / NONE)
    """ 
    # 🎯 OVERRIDE: Fetch a clean historical multi-day block straight from yfinance 
    try:
        ticker_obj = yf.Ticker(TICKER)
        raw_df = ticker_obj.history(period="5d", interval="1m")
        if not raw_df.empty:
            df = raw_df
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Independent yFinance download fallback active | {e}")

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

    # 2. EXTRACT PRE-TRANSFORMED DATA ARRAYS
    ha_open  = df['Open'].to_numpy()
    ha_high  = df['High'].to_numpy()
    ha_low   = df['Low'].to_numpy()
    ha_close = df['Close'].to_numpy()

    # 3. NATIVE TRUE RANGE & SMOOTHED ATR ENGINE (10-PERIOD)
    tr = np.zeros(n)
    for i in range(n):
        if i == 0:
            tr[i] = ha_high[i] - ha_low[i]
        else:
            tr1 = ha_high[i] - ha_low[i]
            tr2 = abs(ha_high[i] - ha_close[i-1])
            tr3 = abs(ha_low[i] - ha_close[i-1])
            tr[i] = max(tr1, tr2, tr3)

    # Replicate TradingView's ta.rma exactly
    atr = np.zeros(n)
    atr_period = 10
    atr_multiplier = 3.0
    
    if n >= atr_period:
        atr[atr_period - 1] = np.mean(tr[0:atr_period])
        for i in range(atr_period, n):
            atr[i] = (tr[i] + (atr_period - 1) * atr[i-1]) / atr_period
    else:
        atr = tr.copy()

    # 4. SUPERTREND TRAILING LOCK IMPLEMENTATION
    hl2 = (ha_high + ha_low) / 2.0
    up_band = hl2 - (atr_multiplier * atr)
    dn_band = hl2 + (atr_multiplier * atr)

    lower_band = np.zeros(n)
    upper_band = np.zeros(n)
    trend_direction = np.ones(n, dtype=int)  # 1 = BULL, -1 = BEAR

    lower_band = up_band
    upper_band = dn_band

    for i in range(1, n):
        lower_band[i] = max(up_band[i], lower_band[i-1]) if ha_close[i-1] > lower_band[i-1] else up_band[i]
        upper_band[i] = min(dn_band[i], upper_band[i-1]) if ha_close[i-1] < upper_band[i-1] else dn_band[i]

        if trend_direction[i-1] == 1:
            trend_direction[i] = -1 if ha_close[i] < lower_band[i] else 1
        else:
            trend_direction[i] = 1 if ha_close[i] > upper_band[i] else -1

    supertrend_line = np.where(trend_direction == 1, lower_band, upper_band)
    
    df['pxy_st_line'] = supertrend_line
    df['bar_count_session'] = np.arange(1, n + 1)
    df['src_c'] = ha_close
    
    # 5. ISOLATED FIVE-STATE DUAL PIPELINE CALCULATION LOOP
    st_signal_history = [] 
    st_trend_history = []
    
    for i in range(n): 
        # Base status parameters for the trend pipe fallback states
        raw_regime = "BULL" if trend_direction[i] == 1 else "BEAR"

        if i < 1: 
            st_signal_history.append("NONE") 
            st_trend_history.append(raw_regime)
            continue 

        # --- PIPE 1 ENGINE: PURE HEIKIN-ASHI GATES ---
        is_current_green = ha_close[i] > ha_open[i]
        is_current_red   = ha_close[i] < ha_open[i]
        is_current_flat  = ha_close[i] == ha_open[i]

        ha_flip_up   = is_current_green and (ha_close[i-1] <= ha_open[i-1])
        ha_flip_down = is_current_red and (ha_close[i-1] >= ha_open[i-1])

        if ha_flip_up:
            st_signal_history.append("BUY")
        elif ha_flip_down:
            st_signal_history.append("SELL")
        elif is_current_green:
            st_signal_history.append("BULL")
        elif is_current_red:
            st_signal_history.append("BEAR")
        else:
            st_signal_history.append("NONE")

        # --- PIPE 2 ENGINE: PURE 10:3 SUPERTREND GATES ---
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
    
    return df

def export_supertrend_json(output_file="../syschrtpxy.json"):
    """Dumps EVERY single candle printed since today's opening bell straight to the JSON file."""
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
        
        if DEBUG_MODE:
            print(f"--- PXY STRATEGY EVALUATION SUMMARY ---")
            print(f"Target Row Lookup Index   -> {idx}")
            print(f"Active Live Market SIGNAL  -> {active_signal}")
            print(f"Active Live Market TREND   -> {active_trend}\n")
            
        return active_signal, active_trend
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Master Output Routing Module Exception: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("\n[PXY STRND ENGINE] Standalone Isolated Dual-Pipe Listener Initiated.")
    dummy = pd.DataFrame()
    signal, trend = get_signal(dummy)
