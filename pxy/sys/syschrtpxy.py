import json
import pandas as pd

from sysdtafpxy import fetch_yf_data
from sysstrndpxy import calculate_supertrend


def export_supertrend_json(output_file="syschrtpxy.json", lookback=42):
    """
    Fetch data → compute SuperTrend → export last N rows to JSON
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
            "close": float(row["Close"]),
            "st": float(row["ST"]),
            "st_trend": str(row["ST_Trend"])
        })

    # =========================
    # WRITE FILE
    # =========================
    with open(output_file, "w") as f:
        json.dump(output, f, indent=2)

    print(f"JSON updated: {output_file} ({len(output)} rows)")
    return output


# =========================
# SELF RUN
# =========================
if __name__ == "__main__":
    export_supertrend_json()
