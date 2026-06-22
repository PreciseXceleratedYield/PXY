# =============================================================================== #
# UNIFIED ENGINE: DYNAMIC PROPORTIONAL OPTION DEPTH MA 7 (UNCAPPED PIPELINE)     #
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
# Dynamic Integration: Import depth metrics from your script
from syshkinpxy import detect_pxy_flip_signal

DEBUG_MODE = False
CHECK_CONFIRMED_ONLY = False # False = reads running live candle (index -1)

def export_supertrend_json(df: pd.DataFrame, output_file=None) -> list:
    """Dumps metrics using backward-compatible mapping keys to protect downstream."""
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
    """Computes TSMA using a 7 baseline modified by absolute option depth difference."""
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
    sma_line_42 = np.zeros(n)
    
    # Pre-calculate standard 42 SMA for structural coupling requirements
    df_sma = df['Close'].rolling(window=42, min_periods=1).mean().to_numpy()
    
    # Baseline period constant
    BASE_PERIOD = 7
    
    # Fast OLS Line rolling projection loop with dynamic window adjustment
    for i in range(n):
        # Step A: Slice data up to the current bar to mock real-time index sequence
        current_sliced_df = df.iloc[:i+1]
        
        # Step B: Safe extraction of Option Matrix parameters from syshkinpxy
        try:
            _, _, ce_depth, pe_depth = detect_pxy_flip_signal(df=current_sliced_df)
            # Step C: Dynamic Formulation -> 7 + absolute difference(pe_depth - ce_depth)
            p = BASE_PERIOD + abs(int(ce_depth) - int(pe_depth))
        except Exception:
            p = BASE_PERIOD # Production runtime fallback boundary layer
            
        # Absolute boundary validation clamp
        if p < 2:
            p = 2
            
        # Verify execution historical window boundary limits 
        if i < (p - 1):
            tsma_line[i] = src_close[i]
            continue
            
        # Standardize local lookback vector space metrics
        x = np.arange(p)
        x_mean = x.mean()
        x_deviations = x - x_mean
        x_var = np.sum(x_deviations ** 2)
        
        y_slice = src_close[i - p + 1 : i + 1]
        
        # Guard against zero variance anomalies
        if x_var == 0:
            tsma_line[i] = src_close[i]
            continue
            
        slope = np.sum(x_deviations * y_slice) / x_var
        intercept = y_slice.mean() - (slope * x_mean)
        tsma_line[i] = (slope * (p - 1)) + intercept

    # Direct logic comparison arrays
    trend_direction = np.where(src_close >= tsma_line, 1, -1)
    
    # Correct zero-boundary lag holes
    for i in range(1, BASE_PERIOD):
        if i < n:
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
    df['sma_line_42'] = df_sma # Decoupled persistent 42 SMA column
    df['sma_trend'] = sma_trend_history
    
    # --- DOWNSTREAM ALIAS COMPATIBILITY LAYER ---
    df['pxy_sma_line'] = tsma_line
    df['sma_trend_full'] = sma_trend_history
    df['src_c'] = src_close
    df['pxy_st_line'] = tsma_line
    df['st_trend_full'] = sma_trend_history
    df['ST'] = tsma_line
    df['ST_Trend'] = sma_trend_history
    df['P_Master'] = src_close
    df['shared_atr'] = 7.0 
    
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
    print("--- STARTING UNIFIED LIVE TIME SERIES MA 7 OPTION DEPTH PIPELINE ---")
    live_df = pd.DataFrame()
    processed_df = calculate_supertrend(live_df)
    
    if not processed_df.empty:
        print(f"[SUCCESS] Calculated. Total Rows: {len(processed_df)}")
        export_supertrend_json(processed_df)
        print(f"[STATUS] Active Pipeline Signal: {get_signal(processed_df)}")
    else:
        print("[WARNING] Engine execution finished with an empty dataset.")

