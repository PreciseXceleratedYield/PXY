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
    PXY® Engine Strategy Matrix - Direct BUY/SELL and Macro Trend Tracker.
    Bypasses truncated upstream slices by fetching fresh day session histories.
    Accepts pre-transformed Heikin-Ashi data arrays directly to run trailing locks.
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

    # 1. TIMELINE ISOLATION: FILTER FOR TODAY'S SESSION CANDLES ONLY (09:15 AM to 15:40 PM)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    if df.index.tz is None:
        df = df.tz_localize('UTC').tz_convert(tz_string)
    else:
        df = df.tz_convert(tz_string)
        
    today_date = datetime.now(pytz.timezone(tz_string)).date()
    day_specific_df = df[df.index.date == today_date].copy()
    
    # If today's session is active, commit to it entirely
    if not day_specific_df.empty:
        df = day_specific_df
    
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

    # Replicate Pine Script's ta.rma (TradingView's exponential moving average for ATR)
    atr = np.zeros(n)
    atr_period = 10
    atr_multiplier = 3.0
    
    if n > 0:
        atr = tr.copy()
    for i in range(1, n):
        atr[i] = (tr[i] + (atr_period - 1) * atr[i-1]) / atr_period

    # 4. ORIGINAL SUPERTREND BAND TRAILING LOCK GATES
    hl2 = (ha_high + ha_low) / 2.0
    up_band = hl2 - (atr_multiplier * atr)
    dn_band = hl2 + (atr_multiplier * atr)

    lower_band = np.zeros(n)
    upper_band = np.zeros(n)
    trend_direction = np.ones(n, dtype=int)  # 1 = BULL, -1 = BEAR

    # Initialize first index boundaries cleanly as arrays
    lower_band[0] = up_band[0]
    upper_band[0] = dn_band[0]
    trend_direction[0] = 1

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
    
    # Code continues smoothly into Part 2...

    # Code continues smoothly into Part 2...

    # 5. CONSOLIDATED CONCURRENT SIGNAL MATRIX GENERATOR
    st_signal_history = [] 
    st_trend_history = []
    
    for i in range(n): 
        current_trend = "BULL" if trend_direction[i] == 1 else "BEAR"
        st_trend_history.append(current_trend)

        if i < 1: 
            st_signal_history.append(current_trend) 
            continue 

        # --- LAYER A: NATIVE SUPERTREND REGIME CROSSOVERS ---
        cross_buy  = (trend_direction[i] == 1)  and (trend_direction[i-1] == -1)
        cross_sell = (trend_direction[i] == -1) and (trend_direction[i-1] == 1)
        
        # --- LAYER B: TREND-FOLLOWING CONTINUATION FLIPS ---
        is_candle_green = ha_close[i] > ha_open[i]
        is_candle_red   = ha_close[i] < ha_open[i]
        
        run_up = (trend_direction[i] == 1)  and is_candle_green and (ha_close[i-1] <= ha_open[i-1])
        run_dn = (trend_direction[i] == -1) and is_candle_red   and (ha_close[i-1] >= ha_open[i-1])

        # Flatten outputs directly to standard execution conditions
        if cross_buy or run_up:
            st_signal_history.append("BUY")   
        elif cross_sell or run_dn:
            st_signal_history.append("SELL")  
        else:
            st_signal_history.append(current_trend)  # Fallback: Represents current HA macro trend state

    df['st_signal_full'] = st_signal_history
    df['st_trend_full'] = st_trend_history
    
    # 🎯 DASHBOARD BACKWARD-COMPATIBILITY KEYS
    df['ST'] = df['pxy_st_line']
    df['ST_Trend'] = df['st_trend_full']
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
        return "NONE", "NONE"
        
    try:
        calculated_df = calculate_supertrend(df)
        n = len(calculated_df)
        
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
    print("\n[PXY STRND ENGINE] Standalone Live Stream Listener Initiated.")
    dummy = pd.DataFrame()
    signal, trend = get_signal(dummy)


