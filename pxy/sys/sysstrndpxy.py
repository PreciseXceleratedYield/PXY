# sysstrndpxy.py
import os
import json
import numpy as np
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from sysdtafpxy import fetch_yf_data
from syscnfgpxy import TIMEZONE

DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Implements a dynamic Supertrend (42, 4.2) engine alongside an isolated 21 SMA.
    The Supertrend value strictly determines the BULL/BEAR trend direction matrix.
    """
    try:
        raw_df = fetch_yf_data(period="3d", interval="1m")
        if raw_df is not None and not raw_df.empty:
            df = raw_df.copy()
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Shared pipeline download fallback active | {e}")
        df = df.copy()

    if df.empty:
        return df

    # Safe Datetime Index Normalisation
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    df = df.tz_localize('UTC').tz_convert(tz_string) if df.index.tz is None else df.tz_convert(tz_string)

    # 1. Calculate isolated 21 SMA for JSON payload continuity
    df['sma21'] = df['Close'].rolling(window=21, min_periods=1).mean()

    # 2. Dynamic Supertrend (42, 4.2) Core Loop Calculation
    st_period = 42
    st_multiplier = 4.2

    # Calculate standard ATR components using High, Low, Close
    high = df['High']
    low = df['Low']
    close = df['Close']
    
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Calculate ATR using Wilder's RMA/EMA convention
    atr = tr.ewm(alpha=1.0 / st_period, min_periods=st_period, adjust=False).mean()
    hl2 = (high + low) / 2

    # Initialize Supertrend tracking arrays
    supertrend_vals = np.zeros(len(df))
    direction_vals = np.ones(len(df)) # 1 = BULL, -1 = BEAR

    up_band = hl2 - (st_multiplier * atr)
    dn_band = hl2 + (st_multiplier * atr)
    
    # Fill defaults for the warmup period
    up_band_prev = up_band.copy()
    dn_band_prev = dn_band.copy()

    # Step-by-step sequential processing loop to track the trailing stop lines cleanly
    for i in range(1, len(df)):
        if pd.isna(atr.iloc[i]):
            continue
            
        # Refine trailing bands relative to the previous price updates
        up_band_prev.iloc[i] = max(up_band.iloc[i], up_band_prev.iloc[i-1]) if close.iloc[i-1] > up_band_prev.iloc[i-1] else up_band.iloc[i]
        dn_band_prev.iloc[i] = min(dn_band.iloc[i], dn_band_prev.iloc[i-1]) if close.iloc[i-1] < dn_band_prev.iloc[i-1] else dn_band.iloc[i]
        
        # Switch trend states or trail the line
        if direction_vals[i-1] == 1:
            if close.iloc[i] < up_band_prev.iloc[i]:
                direction_vals[i] = -1
                supertrend_vals[i] = dn_band_prev.iloc[i]
            else:
                direction_vals[i] = 1
                supertrend_vals[i] = up_band_prev.iloc[i]
        else:
            if close.iloc[i] > dn_band_prev.iloc[i]:
                direction_vals[i] = 1
                supertrend_vals[i] = up_band_prev.iloc[i]
            else:
                direction_vals[i] = -1
                supertrend_vals[i] = dn_band_prev.iloc[i]

    # Map arrays back into the DataFrame structure
    df['st_val'] = supertrend_vals
    df['sma_trend_full'] = np.where(direction_vals == 1, "BULL", "BEAR")
    
    # Enforce data warming filters
    df.loc[pd.isna(atr), 'sma_trend_full'] = "NONE"
    df.loc[pd.isna(atr), 'st_val'] = 0.0

    # COMPATIBILITY ALIASES (Keeps downstream sysdashpxy.py & sysoptionrtpxy.py alive)
    df['ST_Trend'] = df['sma_trend_full']
    df['ST'] = df['st_val']

    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """
    Dumps clean structural data matrix to JSON containing ONLY requested keys.
    """
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
        if df is None or df.empty:
            return None

    output = []
    for idx, row in df.iterrows():
        # Extracted strictly requested 4-key schema payload (Replaced sma50 with st_val)
        output.append({
            "time": str(idx),
            "price": float(row["Close"]),
            "sma21": float(row["sma21"]) if not pd.isna(row["sma21"]) else 0.0,
            "sma50": float(row["st_val"]) if not pd.isna(row["st_val"]) else 0.0
        })

    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY UNIFIED EXCLUSIVE MATRIX ENGINE ---")
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        target_index = processed_df.index[-1]
        print(f"Timestamp   : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"Close Price : {float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"21 SMA Value: {float(processed_df.at[target_index, 'sma21']):.2f}")
        print(f"ST(42,4.2)  : {float(processed_df.at[target_index, 'st_val']):.2f}")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")

