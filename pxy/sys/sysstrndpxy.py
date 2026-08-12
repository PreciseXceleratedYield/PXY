import os
import json
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from sysdtafpxy import fetch_yf_data
from syscnfgpxy import TIMEZONE

DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Maintains function name for external compatibility.
    Calculates a rolling 50-period Averaged Price & SMA straight-line endpoint.
    Naming is kept as 21/50 for downstream system integrity.
    """
    try:
        # Initializing or fetching data
        raw_df = fetch_yf_data(period="3d", interval="1m")
        if raw_df is not None and not raw_df.empty:
            df = raw_df.copy()
    except Exception as e:
        if DEBUG_MODE:
            print(f"Warning: Shared pipeline download fallback active | {e}")
        df = df.copy()

    if df.empty:
        return df

    # Safe Datetime Index Normalization
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    
    tz_string = str(TIMEZONE)
    if df.index.tz is not None:
        df = df.tz_convert(tz_string)
    else:
        df = df.tz_localize('UTC').tz_convert(tz_string)

    # 1. CORE CALCULATION: 50-period Simple Moving Average Vector
    df['sma_core'] = df['Close'].rolling(window=50, min_periods=50).mean()

    # 2. COORDINATE EXTRACTION: 50 bars ago vs. Today
    # Shift by 49 gets the exact starting point of the 50-bar window
    price_past = df['Close'].shift(49)
    sma_past = df['sma_core'].shift(49)

    # 3. HYBRID LOGIC: Averaging Price and SMA at both ends
    # avg_start = (Price 50 bars ago + SMA 50 bars ago) / 2
    avg_start = (price_past + sma_past) / 2.0
    
    # avg_end = (Current Price + Current SMA) / 2
    avg_end = (df['Close'] + df['sma_core']) / 2.0

    # 4. DOWNSTREAM COMPATIBILITY: Map to original indicator keys
    # These represent the terminal endpoint of the straight trend line
    df['st_line'] = avg_end
    df['sma']   = avg_end   
    df['sma']   = avg_end   
    df['ST']      = avg_end

    # Structural Trend State logic
    df['sma_trend_full'] = "BEAR"
    df.loc[df['Close'] > df['st_line'], 'sma_trend_full'] = "BULL"
    df.loc[df['st_line'].isna(), 'sma_trend_full'] = "NONE"
    
    df['ST_Trend'] = df['sma_trend_full']

    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """Maintains exact original function name and schema for JSON export"""
    if df is None or df.empty:
        df = calculate_supertrend(pd.DataFrame())
        if df is None or df.empty:
            return None

    output =
    for idx, row in df.iterrows():
        output.append({
            "time": str(idx),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            # Values expected by your web chart dashboard
            "sma21": float(row["sma"]) if not pd.isna(row["sma"]) else 0.0,
            "sma50": float(row["sma"]) if not pd.isna(row["sma"]) else 0.0 
        })

    # Ensure target directory exists
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
    return output

if __name__ == "__main__":
    print("--- STARTING LIVE PXY UNIFIED EXCLUSIVE MATRIX ENGINE ---")
    processed_df = calculate_supertrend(pd.DataFrame())
    
    if processed_df is not None and not processed_df.empty:
        target_index = processed_df.index[-]
        print(f"Timestamp   : {target_index.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"O:{float(processed_df.at[target_index, 'Open']):.2f} "
              f"C:{float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"Hybrid Value: {float(processed_df.at[target_index, 'sma']):.2f} (50-Bar Avg Method)")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
