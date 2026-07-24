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
    Implements a strict vectorized SMA engine using only 42 SMA.
    Duplicates the 42 SMA calculation across both downstream tracker slots.
    Price above 42 SMA = BULL | Price below 42 SMA = BEAR.
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
    df = df.tz_convert(tz_string) if df.index.tz is not None else df.tz_localize('UTC').tz_convert(tz_string)

    # 1. Calculate Single 42 SMA Line
    df['sma42'] = df['Close'].rolling(window=42, min_periods=1).mean()

    # 2. Establish ST Line by duplicating the 42 SMA
    df['st_line'] = df['sma42']

    # DOWNSTREAM COMPATIBILITY ALIASES (Duplicates 42 SMA into both legacy tracking keys)
    df['sma21'] = df['st_line']   # Maps 42 SMA to the first JSON/Chart placeholder
    df['sma50'] = df['sma42']     # Maps 42 SMA to the second JSON/Chart placeholder
    df['ST'] = df['st_line']

    # 3. Direct Price Trend Verification Engine
    # Price ABOVE 42 SMA is BULL | Price BELOW 42 SMA is BEAR
    df['sma_trend_full'] = np.where(df['Close'] > df['st_line'], "BULL", "BEAR")
    df.loc[df['st_line'].isna(), 'sma_trend_full'] = "NONE"
    
    df['ST_Trend'] = df['sma_trend_full']

    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """
    Dumps clean structural data matrix to JSON matching your exact pipeline contracts.
    """
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
        if df is None or df.empty:
            return None

    output = []
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "sma21": float(row["sma21"]) if not pd.isna(row["sma21"]) else 0.0,   # 42 SMA value
            "sma50": float(row["sma50"]) if not pd.isna(row["sma50"]) else 0.0    # Duplicate 42 SMA value
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
        print(f"O:{float(processed_df.at[target_index, 'Open']):.2f} H:{float(processed_df.at[target_index, 'High']):.2f} L:{float(processed_df.at[target_index, 'Low']):.2f} C:{float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"ST Line Value: {float(processed_df.at[target_index, 'sma21']):.2f} (Pure SMA 42)")
        print(f"SMA 42 Line  : {float(processed_df.at[target_index, 'sma50']):.2f} (Duplicate Placeholder)")
        print(f"Trend State  : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
