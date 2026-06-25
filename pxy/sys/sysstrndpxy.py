"""
===============================================================================
PXY GEOMETRIC ENGINE CORE SYSTEM DOCUMENTATION MASTER INDEX
===============================================================================
ULTRA-SIMPLE PRICE VS 42 SMA SYSTEM (MODE 5 REPLACEMENT)
1. NORTH State - Formula: Close Price > 42 SMA
2. SOUTH State - Formula: Close Price < 42 SMA
3. EQUAL State - Lookback to previous candle to define direction (-2 condition)

UNIFIED PIPE: Confirmed Closed Candle (Index -2) for absolute structural safety
===============================================================================
"""
import os
import sys
import json
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

# Global Configuration
DEBUG_MODE = True

def export_supertrend_json(df: pd.DataFrame, output_file=None) -> list:
    """
    Dumps metrics using backward-compatible mapping keys. 
    Considers only the 42 SMA for structural line mappings.
    """
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
            "st": float(row["sma42"]),  
            "st_trend": str(row["ST_Trend"]),
            "sma_line": float(row["sma42"]),  
            "sma_trend": str(row["ST_Trend"])
        })
        
    out_dir = os.path.dirname(output_file)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)
        
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)
        
    return output

def calculate_direction_for_all_rows(df: pd.DataFrame) -> list:
    """
    Computes trend state based strictly on Price (Close) vs 42 SMA.
    If Close == 42 SMA, it drops back iteratively to find the preceding trend state.
    """
    trends = []
    close_vals = df['Close'].to_numpy()
    s42_vals = df['sma42'].to_numpy()
    
    for i in range(len(df)):
        if pd.isna(close_vals[i]) or pd.isna(s42_vals[i]):
            trends.append("NONE")
            continue
            
        # Price vs 42 SMA structural evaluation
        if close_vals[i] > s42_vals[i]:
            trends.append("NORTH")
        elif close_vals[i] < s42_vals[i]:
            trends.append("SOUTH")
        else:
            # Tiebreaker logic: crawl backward until an unequal state resolves
            lookback_idx = i - 1
            resolved_trend = "NONE"
            while lookback_idx >= 0:
                if pd.isna(close_vals[lookback_idx]) or pd.isna(s42_vals[lookback_idx]):
                    break
                if close_vals[lookback_idx] > s42_vals[lookback_idx]:
                    resolved_trend = "NORTH"
                    break
                elif close_vals[lookback_idx] < s42_vals[lookback_idx]:
                    resolved_trend = "SOUTH"
                    break
                lookback_idx -= 1
            trends.append(resolved_trend)
            
    return trends

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: Refactored Price vs SMA Processor
    - Computes 42 period Simple Moving Average on historical data.
    - Generates direction arrays using Close vs 42 SMA logic.
    - Tail slices to 50 rows for strict compliance with charts and logs.
    """
    df = df.copy()
    
    # 1. Compute basic 42 SMA rolling average straight from dataset
    df['sma42'] = df['Close'].rolling(window=42).mean()
    
    # 2. Assign system trends based on simple structural cross logic
    df['ST_Trend'] = calculate_direction_for_all_rows(df)
    
    # --- DOWNSTREAM ALIAS COMPATIBILITY LAYER ---
    df['ST'] = df['sma42']
    df['sma_line'] = df['sma42']
    df['sma_trend'] = df['ST_Trend']
    
    # 3. Slice the clean matrix down to exactly 50 rows AFTER calculations are complete
    df = df.tail(50).copy()
    df['bar_count'] = np.arange(1, 51)
    return df

def get_signal(df=None):
    """
    Downstream communication port processing execution metrics.
    Uses the stable, fully complete confirmed candle (Index -2) to prevent repainting.
    Returns: (confirmed_signal, confirmed_signal) matching the pipeline logic.
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or len(df) < 44:  # Safety data lookback boundary check
        return "NONE", "NONE"
        
    try:
        # Run calculation architecture on history matrix
        df_st = calculate_supertrend(df)
        
        # Pull stable historical row indexes for crossover evaluation
        trend_minus_3 = str(df_st['ST_Trend'].iloc[-3])
        trend_minus_2 = str(df_st['ST_Trend'].iloc[-2])
        
        # --- UNIFIED PIPELINE (Index -2: Confirmed Closed Bar) ---
        if trend_minus_3 != "NORTH" and trend_minus_2 == "NORTH":
            confirmed_signal = "BUY"
        elif trend_minus_3 != "SOUTH" and trend_minus_2 == "SOUTH":
            confirmed_signal = "SELL"
        else:
            confirmed_signal = trend_minus_2  # Standard trend continuation state (NORTH/SOUTH)
            
        # Return matched states across both tracking positions for absolute system harmony
        return confirmed_signal, confirmed_signal
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Error: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("=== Upgraded Simple Close vs 42 SMA Geometric Engine Self-Test ===")
    
    raw_df = fetch_yf_data()
    
    if raw_df is not None and not raw_df.empty:
        processed_df = calculate_supertrend(raw_df)
        print(f"[SUCCESS] Calculated Matrix. Sliced Rows for Export: {len(processed_df)}")
        
        # Execute chart synchronization export
        export_supertrend_json(processed_df)
        
        entry_sig, exit_sig = get_signal(raw_df)
        print(f"CURRENT CONSTRUCT SIGNAL (CONFIRMED ENTRY): {entry_sig}")
        print(f"CURRENT CONSTRUCT SIGNAL (CONFIRMED EXIT): {exit_sig}")
    else:
        print("[WARNING] Upstream connection returned an empty historical matrix.")



