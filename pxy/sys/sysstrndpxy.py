# =============================================================================== #
# UNIFIED ENGINE: FAST 1:1 TIME SERIES MOVING AVERAGE 7 WITH DOWNSTREAM COUPLING  #
# =============================================================================== #
import os
import sys
import json
import numpy as np
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from sysdtafpxy import fetch_yf_data
from syscnfgpxy import TIMEZONE

DEBUG_MODE = False
CHECK_CONFIRMED_ONLY = False  # False = reads running live candle (index -1)

def export_supertrend_json(df: pd.DataFrame, output_file=None) -> list:
    """Dumps TSMA(7) metrics using backward-compatible mapping keys to protect downstream."""
    if df is None or df.empty:
        return []

    if output_file is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_file = os.path.abspath(os.path.join(base_dir, "web", "webchrtpxy.json"))

    output = []
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "close": float(row["Close"]),
            "p_master": float(row["Close"]),
            "st": float(row["ST"]),           
            "st_trend": str(row["ST_Trend"]),
            "sma_line": float(row["sma_line"]),
            "sma_trend": str(row["sma_trend"])
        })

    out_dir = os.path.dirname(output_file)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
        
    return output

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """Computes TSMA 7 via rolling OLS and maps legacy aliases to preserve downstream scripts."""
    if df is None or df.empty:
        try:
            df = fetch_yf_data(period="3d", interval="1m")
            if df is None or df.empty:
                return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    df = df.copy()
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_str = str(TIMEZONE)
    df = df.tz_localize('UTC').tz_convert(tz_str) if df.index.tz is None else df.tz_convert(tz_str)
    
    n = len(df)
    if n == 0:
        return df

    src_close = df['Close'].to_numpy()
    tsma_line = np.zeros(n)

    # --- VECTORIZED LINEAR REGRESSION SETUP ---
    p = 7
    x = np.arange(p)
    x_mean = x.mean()
    x_deviations = x - x_mean
    x_var = np.sum(x_deviations ** 2)

    # Fast OLS Line rolling projection loop
    for i in range(n):
        if i < (p - 1):
            tsma_line[i] = src_close[i]
            continue
        
        y_slice = src_close[i - p + 1 : i + 1]
        y_mean = y_slice.mean()
        slope = np.sum(x_deviations * (y_slice - y_mean)) / x_var
        tsma_line[i] = (slope * (p - 1 - x_mean)) + y_mean

    # Direct logic comparison arrays 
    trend_direction = np.where(src_close >= tsma_line, 1, -1)
    
    # Correct zero-boundary lag holes
    for i in range(1, p - 1):
        trend_direction[i] = 1 if src_close[i] >= src_close[i-1] else -1

    # Native state generation tracking
    sma_trend_history = []
    for i in range(n):
        regime = "BULL" if trend_direction[i] == 1 else "BEAR"
        if i < 1:
            sma_trend_history.append(regime)
            continue
            
        if trend_direction[i] == 1 and trend_direction[i-1] == -1:
            sma_trend_history.append("BUY")
        elif trend_direction[i] == -1 and trend_direction[i-1] == 1:
            sma_trend_history.append("SELL")
        else:
            sma_trend_history.append(regime)

    # --- PRODUCTION STATE RETURN VALUES ---
    df['sma_line'] = tsma_line
    df['sma_trend'] = sma_trend_history

    # --- 🎯 DOWNSTREAM ALIAS COMPATIBILITY LAYER ---
    df['pxy_sma_line'] = tsma_line
    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close
    df['pxy_st_line'] = tsma_line
    df['st_trend_full'] = sma_trend_history
    df['ST'] = tsma_line
    df['ST_Trend'] = sma_trend_history
    df['P_Master'] = src_close
    df['shared_atr'] = 12.0

    return df

def get_signal(df: pd.DataFrame) -> str:
    """Unpacks and returns the clean active pipeline trend signal state."""
    if df is None or df.empty:
        df = pd.DataFrame()
        
    try:
        calc_df = calculate_supertrend(df)
        n = len(calc_df)
        if n < 2:
            return "NONE"
        
        idx = n - 2 if CHECK_CONFIRMED_ONLY else n - 1  
        return str(calc_df.at[calc_df.index[idx], 'sma_trend']).upper().strip()
    except Exception:
        return "NONE"

if __name__ == "__main__":
    print("--- STARTING UNIFIED LIVE TIME SERIES MA 7 ENGINE ---")
    live_df = pd.DataFrame()
    processed_df = calculate_supertrend(live_df)
    if not processed_df.empty:
        print(f"[SUCCESS] Calculated. Total Rows: {len(processed_df)}")
        export_supertrend_json(processed_df)
