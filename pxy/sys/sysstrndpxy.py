# =============================================================================== #
# UNIFIED ENGINE: DYNAMIC ATR LOOKBACK TIME SERIES MA WITH DOWNSTREAM COUPLING    #
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
CHECK_CONFIRMED_ONLY = False # False = reads running live candle (index -1)
ATR_PERIOD = 14

def calculate_atr(df: pd.DataFrame, period=ATR_PERIOD) -> pd.Series: 
    """Computes session-grouped True Range series with a production fallback boundary cap."""
    df_local = df.copy()
    if not isinstance(df_local.index, pd.DatetimeIndex):
        df_local.index = pd.to_datetime(df_local.index)
        
    high, low, close = df_local['High'], df_local['Low'], df_local['Close'] 
    prev_close = close.shift(1) 
    
    tr = pd.concat([
        high - low, 
        (high - prev_close).abs(), 
        (low - prev_close).abs()
    ], axis=1).max(axis=1) 
    
    date_groups = df_local.index.date
    atr = tr.groupby(date_groups, group_keys=False).apply(
        lambda x: x.rolling(window=period, min_periods=1).mean()
    )
    
    return atr.apply(lambda x: 12.0 if (x == 0 or pd.isna(x) or x > 12.0) else x)

def export_supertrend_json(df: pd.DataFrame, output_file=None) -> list:
    """Dumps dynamic metric metrics using backward-compatible mapping keys."""
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
    """Computes TSMA using a dynamic, rounded ATR lookback window with a strict floor of 7."""
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

    # Calculate and round the ATR array for lookback calculation
    atr_series = calculate_atr(df, period=ATR_PERIOD)
    rounded_atr = np.round(atr_series.to_numpy())
    src_close = df['Close'].to_numpy()
    tsma_line = np.zeros(n)
    
    # Fast OLS Line rolling projection loop with dynamic execution bounds
    for i in range(n):
        # Enforce dynamic lookback window with a absolute floor value of 7
        raw_p = rounded_atr[i] if not np.isnan(rounded_atr[i]) else 7
        p = int(max(7, raw_p))
        
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
    
    # Correct zero-boundary lag holes up to absolute floor boundary
    for i in range(1, 6):
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
    df['shared_atr'] = atr_series.to_numpy()
    
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
    print("--- STARTING UNIFIED LIVE TIME SERIES MA (DYNAMIC MIN 7) ENGINE ---")
    live_df = pd.DataFrame()
    processed_df = calculate_supertrend(live_df)
    
    if not processed_df.empty:
        print(f"[SUCCESS] Calculated. Total Rows: {len(processed_df)}")
        export_supertrend_json(processed_df)
        print(f"[STATUS] Active Pipeline Signal: {get_signal(processed_df)}")
    else:
        print("[WARNING] Engine execution finished with an empty dataset.")
