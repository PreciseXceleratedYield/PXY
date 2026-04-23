import json
import pandas as pd
import os

from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend


def export_supertrend_json(output_file="../syschrtpxy.json", lookback=42):
    """
    Fetch data → compute SuperTrend → export last N rows with OHLC to JSON
    """

    # =========================
    # FETCH DATA
    # =========================
    df = fetch_yf_data()

    if df is None or df.empty:
        print("No data fetched")
        return None

    # =========================
    # SUPER TREND
    # =========================
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
        output.append({
            "time": str(idx),

            # -------------------------
            # OHLC DATA (ADDED)
            # -------------------------
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),

            # -------------------------
            # SUPER TREND DATA
            # -------------------------
            "st": float(row["ST"]),
            "st_trend": str(row["ST_Trend"])
        })

    # =========================
    # WRITE FILE (PARENT DIR)
    # =========================
    if os.path.dirname(output_file):
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    return output


# =========================
# SELF RUN
# =========================
if __name__ == "__main__":
    export_supertrend_json()
