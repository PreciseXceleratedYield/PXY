"""
# sysstrndpxy.py 
===============================================================================
PXY GEOMETRIC ENGINE CORE SYSTEM DOCUMENTATION MASTER INDEX
===============================================================================
ULTRA-SIMPLE MOVING AVERAGE CROSSOVER SYSTEM (MODE 5 REPLACEMENT)
1. NORTH State - Formula: 21 SMA > 42 SMA
2. SOUTH State - Formula: 21 SMA < 42 SMA
3. EQUAL State - Lookback to previous candle to define direction (-2 condition)

ENTRY PIPE: Confirmed Closed Candle (Index -2)
EXIT PIPE: Running Live Candle (Index -1)
===============================================================================
"""
import os
import sys
import json
import pandas as pd
import numpy as np
from sysdtafpxy import fetch_yf_data

DEBUG_MODE = True

def export_supertrend_json(df: pd.DataFrame, output_file=None) -> list:
    """Dumps metrics using backward-compatible mapping keys. Considers only 42 SMA for lines."""
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
            "st": float(row["sma42"]),  # Configured strictly to 42 SMA
            "st_trend": str(row["ST_Trend"]),
            "sma_line": float(row["sma42"]),  # Configured strictly to 42 SMA
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
    Computes trend state for every row in the historical matrix.
    If 21 SMA == 42 SMA, it drops back iteratively (-2 condition) to find the trend state.
    """
    trends = []
    s21_vals = df['sma21'].to_numpy()
    s42_vals = df['sma42'].to_numpy()
    
    for i in range(len(df)):
        if pd.isna(s21_vals[i]) or pd.isna(s42_vals[i]):
            trends.append("NONE")
            continue
            
        # Standard crossover checks
        if s21_vals[i] > s42_vals[i]:
            trends.append("NORTH")
        elif s21_vals[i] < s42_vals[i]:
            trends.append("SOUTH")
        else:
            # Tiebreaker logic: crawl backward through the array until a trend is resolved
            lookback_idx = i - 1
            resolved_trend = "NONE"
            while lookback_idx >= 0:
                if pd.isna(s21_vals[lookback_idx]) or pd.isna(s42_vals[lookback_idx]):
                    break
                if s21_vals[lookback_idx] > s42_vals[lookback_idx]:
                    resolved_trend = "NORTH"
                    break
                elif s21_vals[lookback_idx] < s42_vals[lookback_idx]:
                    resolved_trend = "SOUTH"
                    break
                lookback_idx -= 1
            trends.append(resolved_trend)
            
    return trends

def calculate_supertrend(df: pd.DataFrame) -> pd.DataFrame:
    """
    PXY® Engine: Refactored SMA Crossover Processor
    - Computes 21 and 42 period Simple Moving Averages on full history data.
    - Generates direction arrays processing the tiebreaker equality loop.
    - Tail slices to 50 rows for strict compliance with charts and logging buffers.
    """
    df = df.copy()
    
    # 1. Compute basic rolling averages straight from dataset
    df['sma21'] = df['Close'].rolling(window=21).mean()
    df['sma42'] = df['Close'].rolling(window=42).mean()
    
    # 2. Assign system trends based on simple structural cross logic
    df['ST_Trend'] = calculate_direction_for_all_rows(df)
    
    # --- DOWNSTREAM ALIAS COMPATIBILITY LAYER ---
    # Enforces 42 SMA line assignment across core structural variables
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
    Separates Entry signals (Confirmed Index -2) and Exit signals (Running Live Index -1).
    Detects physical line crossovers to output BUY / SELL trigger signals.
    """
    if df is None:
        df = fetch_yf_data()
        
    if df is None or len(df) < 42:
        return "NONE", "NONE"
        
    try:
        # Run calculations on pure raw history first to shield rolling calculations
        df_st = calculate_supertrend(df)
        
        # Pull required history rows for crossover confirmation
        # Index -3: Previous Confirmed, Index -2: Current Confirmed, Index -1: Live Running
        trend_minus_3 = str(df_st['ST_Trend'].iloc[-3])
        trend_minus_2 = str(df_st['ST_Trend'].iloc[-2])
        trend_minus_1 = str(df_st['ST_Trend'].iloc[-1])
        
        # --- ENTRY PIPE (Index -2: Confirmed Closed Bar) ---
        if trend_minus_3 != "NORTH" and trend_minus_2 == "NORTH":
            entry_signal = "BUY"
        elif trend_minus_3 != "SOUTH" and trend_minus_2 == "SOUTH":
            entry_signal = "SELL"
        else:
            entry_signal = trend_minus_2  # Standard state (NORTH/SOUTH/NONE)
            
        # --- EXIT PIPE (Index -1: Live Running Bar) ---
        if trend_minus_2 != "NORTH" and trend_minus_1 == "NORTH":
            exit_signal = "BUY"
        elif trend_minus_2 != "SOUTH" and trend_minus_1 == "SOUTH":
            exit_signal = "SELL"
        else:
            exit_signal = trend_minus_1  # Standard state (NORTH/SOUTH/NONE)
            
        return entry_signal, exit_signal
        
    except Exception as e:
        if DEBUG_MODE:
            print(f"PXY Error: {e}")
        return "NONE", "NONE"

if __name__ == "__main__":
    print("=== Upgraded Simple 21/42 SMA Geometric Engine Self-Test ===")
    
    # Ingest data through upstream data feed
    raw_df = fetch_yf_data()
    
    if raw_df is not None and not raw_df.empty:
        # Step 1: Compute metrics on the complete history to protect the moving average lookback
        processed_df = calculate_supertrend(raw_df)
        print(f"[SUCCESS] Calculated Matrix. Sliced Rows for Export: {len(processed_df)}")
        
        # Step 2: Fire structural JSON dumping matrix engine (Exports the 50-row slice)
        export_supertrend_json(processed_df)
        
        # Step 3: Pull system status split pipelines
        entry_sig, exit_sig = get_signal(raw_df)
        print(f"CURRENT ENTRY SIGNAL (CONFIRMED): {entry_sig}")
        print(f"CURRENT EXIT SIGNAL (RUNNING): {exit_sig}")
    else:
        print("[WARNING] Upstream connection returned an empty historical matrix.")




