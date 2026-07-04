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
from syscnfgpxy import TIMEZONE, TICKER

DEBUG_MODE = False 
CHECK_CONFIRMED_ONLY = False  

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    Implements a strict 21/50 SMA matrix using explicit mutually exclusive states.
    Uses inclusive operators (>=, <=) to eliminate mathematical ties without an else statement.
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
    df = df.tz_localize('UTC').tz_convert(tz_string) if df.index.tz is None else df.tz_convert(tz_string)
        
    n = len(df)
    if n == 0:
        return df

    # --- Moving Average Parameters ---
    sma21_length = 21
    sma50_length = 50     

    # Calculate SMAs using standard pandas rolling windows
    df['sma21'] = df['Close'].rolling(window=sma21_length, min_periods=1).mean()
    df['sma50'] = df['Close'].rolling(window=sma50_length, min_periods=1).mean()

    src_close = df['Close'].to_numpy()
    sma21 = df['sma21'].to_numpy()
    sma50 = df['sma50'].to_numpy()

    # --- Custom Matrix Logic with Mutually Exclusive Rules ---
    custom_regime_history = []
    for i in range(n): 
        close_val = src_close[i]
        s21 = sma21[i]
        s50 = sma50[i]

        # Handle startup warm up rows safely
        if i < 1:
            start_bull = (close_val >= s21) and (s21 >= s50)
            start_bear = (close_val < s21) and (s21 < s50)
            start_hside = (s21 >= s50) and (close_val <= s21)
            start_lside = (s21 < s50) and (close_val > s21)
            
            if start_bull:
                custom_regime_history.append("BULL")
            if start_bear:
                custom_regime_history.append("BEAR")
            if start_hside:
                custom_regime_history.append("HSIDE")
            if start_lside:
                custom_regime_history.append("LSIDE")
            continue

        # 1. Active Cross Triggers
        is_cross_buy  = (close_val > s21) and (src_close[i-1] <= sma21[i-1])
        is_cross_sell = (close_val < s21) and (src_close[i-1] >= sma21[i-1])

        # 2. Structural Regime States (Inclusive operators absorb ties perfectly)
        is_bull_regime  = (not is_cross_buy) and (not is_cross_sell) and (close_val > s21) and (s21 >= s50)
        is_bear_regime  = (not is_cross_buy) and (not is_cross_sell) and (close_val < s21) and (s21 < s50)
        is_hside_regime = (not is_cross_buy) and (not is_cross_sell) and (s21 >= s50) and (close_val <= s21)
        is_lside_regime = (not is_cross_buy) and (not is_cross_sell) and (s21 < s50) and (close_val >= s21)

        # Initialize tracking reference state
        state = "NONE"

        # Sequential independent condition triggers
        if is_cross_buy:
            state = "BUY"
        if is_cross_sell:
            state = "SELL"
        if is_bull_regime:
            state = "BULL"
        if is_bear_regime:
            state = "BEAR"
        if is_hside_regime:
            state = "HSIDE"
        if is_lside_regime:
            state = "LSIDE"

        custom_regime_history.append(state)

    # --- Direct Injection Pipeline to Match JSON UI Server Layout Exactly ---
    df['exit'] = custom_regime_history
    df['pxy_sma_line'] = sma21       
    df['sma_trend_full'] = custom_regime_history
    df['src_c'] = src_close 
    
    df['pxy_st_line'] = df['pxy_sma_line']
    df['st_trend_full'] = df['sma_trend_full']
    df['ST'] = df['pxy_sma_line']
    df['ST_Trend'] = df['sma_trend_full']
    df['P_Master'] = df['src_c']
    df['shared_atr'] = np.zeros(n) 
    
    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """ Dumps exact candle framework data matrix directly to JSON with exit fields """
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
            "sma_trend": str(row["sma_trend_full"]),
            "exit": str(row["sma_trend_full"])       
        })

    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY UNIFIED EXCLUSIVE MATRIX ENGINE ---")
    
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        idx_pos = -2 if CHECK_CONFIRMED_ONLY else -1
        target_index = processed_df.index[idx_pos]
        
        print(f"Target Row Index Position -> {idx_pos} ({'CLOSED BAR' if CHECK_CONFIRMED_ONLY else 'LIVE TICK'})")
        print(f"Timestamp   : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"21 SMA Line Matrix Value   : {float(processed_df.at[target_index, 'pxy_sma_line']):.2f}")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
