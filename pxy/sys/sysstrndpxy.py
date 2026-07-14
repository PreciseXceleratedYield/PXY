# sysstrndpxy.py
import os
import json
import numpy as np
import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from sysdtafpxy import fetch_yf_data
from syscnfgpxy import TIMEZONE
# Import the custom 30-length linear regression function
from sysrigpxy import calculate_linear_regression_channel

DEBUG_MODE = False

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    Implements a unified Linear Regression (length 30) direction engine.
    Trend is strictly defined by the standalone regression line slope.
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

    # 1. Process Linear Regression Line (Length 30) from your imported file
    # This automatically updates df with 'linreg_base' and the trailing focus signals
    df = calculate_linear_regression_channel(df, length=30)

    # 2. Retain 50 SMA strictly for operational JSON payload requirements
    df['sma50'] = df['Close'].rolling(window=50, min_periods=1).mean()

    # 3. Synchronize trend variables strictly with the regression module state
    # This inherits the pure BULL/BEAR output calculated inside sysrigpxy
    df['sma_trend_full'] = df['sma_trend_full']

    # RESTORED ALIASES FOR COMPATIBILITY (sysdashpxy.py & sysoptionrtpxy.py)
    df['ST_Trend'] = df['sma_trend_full']
    df['ST'] = df['linreg_base']  

    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """
    Dumps clean structural data matrix to JSON containing OHLC, LinReg base, and 50 SMA.
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
            "linreg_base": float(row["linreg_base"]) if not pd.isna(row["linreg_base"]) else 0.0,
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
        print(f"LinReg Base : {float(processed_df.at[target_index, 'linreg_base']):.2f}")
        print(f"50 SMA Value: {float(processed_df.at[target_index, 'sma50']):.2f}")
        print(f"Trend State : {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")
