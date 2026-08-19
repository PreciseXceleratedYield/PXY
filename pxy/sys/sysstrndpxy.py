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
    Calculates 50 SMA and a true Supertrend (Period 1, Factor 1) using the 50 SMA.
    Fixed crossover logic to use strict historic states to prevent trend jumping.
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

    # 1. Base 50 SMA Calculation
    df['sma_50_core'] = df['Close'].rolling(window=50, min_periods=1).mean()

    # 2. True Supertrend (Period 1, Factor 1) Calculations based on 50 SMA
    high_low = df['High'] - df['Low']
    high_close_prev = (df['High'] - df['Close'].shift(1)).abs()
    low_close_prev = (df['Low'] - df['Close'].shift(1)).abs()
    
    df['tr'] = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    df['atr_1'] = df['tr'].rolling(window=1, min_periods=1).mean()

    # Generate basic bands around the 50 SMA
    factor = 1.0
    df['basic_ub'] = df['sma_50_core'] + (factor * df['atr_1'])
    df['basic_lb'] = df['sma_50_core'] - (factor * df['atr_1'])

    # Implement trailing bands and directional crossover processing
    st_line = []
    st_trend = []
    
    curr_dir = "BULL"  
    prev_ub = 0.0
    prev_lb = 0.0
    prev_sma = 0.0

    for idx, row in df.iterrows():
        sma_val = row['sma_50_core']
        ub_val = row['basic_ub']
        lb_val = row['basic_lb']

        if pd.isna(sma_val) or pd.isna(ub_val) or pd.isna(lb_val):
            st_line.append(sma_val if not pd.isna(sma_val) else 0.0)
            st_trend.append("NONE")
            continue

        # --- STEP 1: Calculate Trailing Final Bands for Current Candle ---
        final_ub = min(ub_val, prev_ub) if prev_ub > 0 and prev_sma < prev_ub else ub_val
        final_lb = max(lb_val, prev_lb) if prev_lb > 0 and prev_sma > prev_lb else lb_val

        # --- STEP 2: Crossover Logic Evaluated Against Prior Step Bands ---
        if curr_dir == "BULL" and sma_val < final_lb:
            curr_dir = "BEAR"
        elif curr_dir == "BEAR" and sma_val > final_ub:
            curr_dir = "BULL"

        # --- STEP 3: Assign Final Active Line Segment ---
        current_st_line = final_lb if curr_dir == "BULL" else final_ub
        st_line.append(current_st_line)
        st_trend.append(curr_dir)

        # Update historical memory variables for next loop iteration
        prev_ub = final_ub
        prev_lb = final_lb
        prev_sma = sma_val

    # 3. Downstream Key Mapping Management
    df['st_line'] = st_line
    df['ST'] = st_line
    df['sma21'] = st_line              
    df['sma50'] = df['sma_50_core']    
    
    df['sma_trend_full'] = st_trend
    df['ST_Trend'] = st_trend

    return df

def export_supertrend_json(df: pd.DataFrame = None, output_file="../web/webchrtpxy.json"):
    """Maintains exact original function structure and keys for downstream compatibility"""
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
        print(f"SMA50 Value (50 SMA Base)  : {float(processed_df.at[target_index, 'sma50']):.2f}")
        print(f"SMA21 Value (ST Line Data) : {float(processed_df.at[target_index, 'sma21']):.2f}")
        print(f"Trend State (True ST Trend): {str(processed_df.at[target_index, 'sma_trend_full'])}")
        export_supertrend_json(processed_df)
    else:
        print("CRITICAL: Upstream data empty.")

