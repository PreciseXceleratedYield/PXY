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

def calculate_sma(series: pd.Series, period: int) -> pd.Series:
    """Helper function to calculate standard Simple Moving Average (SMA)"""
    return series.rolling(window=period).mean()

def calculate_pinescript_atr(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calculates Wilder's RMA (Moving Average used by TradingView for ATR).
    Matches Pine Script's ta.atr(length) functionality exactly.
    """
    high = df['High']
    low = df['Low']
    close_prev = df['Close'].shift(1)
    
    # Calculate True Range (TR)
    tr1 = high - low
    tr2 = (high - close_prev).abs()
    tr3 = (low - close_prev).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Pine Script's ta.rma (Wilder's Exponential Moving Average)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame: 
    """ 
    Implements your customized multi-average strategy pipeline.
    Averages SMA 50, SMA 21, and a dynamic 5/5 Supertrend into a single line,
    while using SMA 21 crossovers and Supertrend states to define a custom regime matrix.
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

    # --- Pine Script Inputs ---
    sma_length = 50
    sma21_length = 21
    st_length = 5
    st_multiplier = 5.0

    # 1. Component One & Two: Calculate Moving Averages
    # Fill early NaNs with raw close series to prevent downstream serialization breaks
    sma50 = calculate_sma(df['Close'], sma_length).fillna(df['Close']).to_numpy()
    sma21 = calculate_sma(df['Close'], sma21_length).fillna(df['Close']).to_numpy()

    # 2. Component Three: Calculate Standard 5-Period ATR for Supertrend
    atr_series = calculate_pinescript_atr(df, st_length).fillna(0.0)
    custom_atr = atr_series.to_numpy()

    # Read necessary pricing arrays
    src_close = df['Close'].to_numpy()
    src_high = df['High'].to_numpy()
    src_low = df['Low'].to_numpy()

    hl2 = (src_high + src_low) / 2.0
    basic_ub = hl2 + (st_multiplier * custom_atr)
    basic_lb = hl2 - (st_multiplier * custom_atr)

    final_ub = np.zeros(n)
    final_lb = np.zeros(n)
    st_line = np.zeros(n)
    trend = np.ones(n) 

    # --- Supertrend Processing Engine ---
    for i in range(n):
        if i == 0:
            final_ub[i] = basic_ub[i]
            final_lb[i] = basic_lb[i]
            st_line[i] = final_ub[i] if src_close[i] <= final_ub[i] else final_lb[i]
            trend[i] = 1 if src_close[i] > st_line[i] else -1
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

        st_line[i] = final_lb[i] if trend[i] == 1 else final_ub[i]

    # --- 3. Mathematical Blend: (SMA 50 + SMA 21 + Supertrend Line) / 3 ---
    # Safe protection against NaN alignment errors early in the dataframe
    combined_line = (sma50 + sma21 + st_line) / 3.0

    # --- 4. Custom Matrix Logic (BUY / SELL / BULL / BEAR / SIDE) ---
    custom_regime_history = []
    for i in range(n): 
        if i < 1: 
            custom_regime_history.append("SIDE")
            continue 

        # Crossover checks for live price crossing SMA 21
        cross_buy  = (src_close[i] > sma21[i]) and (src_close[i-1] <= sma21[i-1])
        cross_sell = (src_close[i] < sma21[i]) and (src_close[i-1] >= sma21[i-1])

        if cross_buy:
            custom_regime_history.append("BUY")
        elif cross_sell:
            custom_regime_history.append("SELL")
        elif (src_close[i] > sma21[i]) and (trend[i] == 1):
            custom_regime_history.append("BULL")
        elif (src_close[i] < sma21[i]) and (trend[i] == -1):
            custom_regime_history.append("BEAR")
        else:
            custom_regime_history.append("SIDE")

    # --- Direct Injection Pipeline to Match JSON UI Server Layout Exactly ---
    df['exit'] = custom_regime_history
    df['pxy_sma_line'] = combined_line       
    df['sma_trend_full'] = custom_regime_history
    df['src_c'] = src_close 
    
    df['pxy_st_line'] = df['pxy_sma_line']
    df['st_trend_full'] = df['sma_trend_full']
    df['ST'] = df['pxy_sma_line']
    df['ST_Trend'] = df['sma_trend_full']
    df['P_Master'] = df['src_c']
    df['shared_atr'] = custom_atr
    
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
    print("--- STARTING LIVE PXY UNIFIED SMA + SMA21 + SUPERTREND ENGINE ---")
    
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        idx_pos = -2 if CHECK_CONFIRMED_ONLY else -1
        target_index = processed_df.index[idx_pos]
        
        print(f"Target Row Index Position -> {idx_pos} ({'CLOSED BAR' if CHECK_CONFIRMED_ONLY else 'LIVE TICK'})")
        print(f"Timestamp   : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"Combined Line Matrix Value: {float(processed_df.at[target_index, 'pxy_sma_line']):.2f}")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")


