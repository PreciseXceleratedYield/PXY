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
    Calculates 50 SMA and maps it cleanly across all required systems.
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

    # Calculate 50 Simple Moving Average using pure pandas (No numpy needed)
    df['sma_50_core'] = df['Close'].rolling(window=50, min_periods=1).mean()

    # CRITICAL: Keep identical column names so no downstream parts break
    df['st_line'] = df['sma_50_core']
    df['sma21'] = df['sma_50_core']   
    df['sma50'] = df['sma_50_core']   
    df['ST'] = df['sma_50_core']

    # Keep structural trend names intact
    df['sma_trend_full'] = "BEAR"
    df.loc[df['Close'] > df['sma_50_core'], 'sma_trend_full'] = "BULL"
    df.loc[df['sma_50_core'].isna(), 'sma_trend_full'] = "NONE"
    
    df['ST_Trend'] = df['sma_trend_full']

    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """Maintains exact original function name for JSON export"""
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
        print(f"O:{float(processed_df.at[target_index, 'Open']):.2f} H:{float(processed_df.at[target_index, 'High']):.2f} L:{float(processed_df.at[target_index, 'Low']):.2f} C:{float(processed_df.at[target_index, 'Close']):.2f}")
        print(f"ST Line Value: {float(processed_df.at[target_index, 'sma21']):.2f} (50 SMA Alternative)")
        print(f"Trend State  : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")

