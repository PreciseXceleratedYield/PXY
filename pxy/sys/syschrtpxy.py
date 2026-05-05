import json
import pandas as pd
import os
import numpy as np
from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend

def export_supertrend_json(output_file="../syschrtpxy.json", lookback=42):
    """
    Fetch data → compute SuperTrend & Master Price → export last N rows
    """
    # =========================
    # FETCH DATA
    # =========================
    df = fetch_yf_data()
    if df is None or df.empty:
        print("No data fetched")
        return None

    # =========================
    # MASTER PRICE CALCULATION (Sync with Engine)
    # =========================
    df = df.copy()
    o = df['Open']
    h = df['High']
    l = df['Low']
    c = df['Close']
    c1 = df['Close'].shift(1)

    e1 = c
    e2 = (c1 + c) / 2
    e3 = (c + o) / 2
    e4 = (o + h + l + c) / 4
    
    df['P_Master'] = (e1 + e2 + e3 + e4) / 4

    # =========================
    # SUPER TREND
    # =========================
    # Note: calculate_supertrend should already return df with 'ST' and 'ST_Trend'
    df = calculate_supertrend(df)

    # =========================
    # LAST N ROWS
    # =========================
    df = df.tail(lookback).copy()

    # =========================
    # BUILD JSON
    # =========================
    output = []
    for idx, row in df.iterrows():
        # Handle potential NaN for the first row's P_Master due to shift(1)
        p_val = float(row["P_Master"]) if not np.isnan(row["P_Master"]) else float(row["Close"])
        
        output.append({
            "time": str(idx),
            "close": float(row["Close"]),
            "p_master": p_val,  # Added the synchronized price
            "st": float(row["ST"]),
            "st_trend": str(row["ST_Trend"])
        })

    # =========================
    # WRITE FILE
    # =========================
    os.makedirs(os.path.dirname(output_file), exist_ok=True) if os.path.dirname(output_file) else None
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    return output

if __name__ == "__main__":
    export_supertrend_json()

