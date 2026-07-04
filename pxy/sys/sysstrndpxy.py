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
    Implements a vectorized 21/50 SMA engine.
    Safely calculates 'sma_trend_full' and 'ST_Trend' for downstream engines/dashboards.
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

    # Core Calculations
    df['sma21'] = df['Close'].rolling(window=21, min_periods=1).mean()
    df['sma50'] = df['Close'].rolling(window=50, min_periods=1).mean()

    # Vectorized Trend Matrix - CRITICAL FOR DOWNSTREAM COMPATIBILITY
    df['sma_trend_full'] = np.where(df['sma21'] >= df['sma50'], "BULL", "BEAR")
    df.loc[df['sma21'].isna() | df['sma50'].isna(), 'sma_trend_full'] = "NONE"

    # RESTORED ALIAS FOR SYSDASHPXY.PY COMPATIBILITY
    df['ST_Trend'] = df['sma_trend_full']

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
        # Extracted strictly requested 4-key schema payload
        output.append({
            "time": str(idx),
            "price": float(row["Close"]),
            "sma21": float(row["sma21"]) if not pd.isna(row["sma21"]) else 0.0,
            "sma50": float(row["sma50"]) if not pd.isna(row["sma50"]) else 0.0
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
        print(f"50 SMA Value: {float(processed_df.at[target_index, 'sma50']):.2f}")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")


