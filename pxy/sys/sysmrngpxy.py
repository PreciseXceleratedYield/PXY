# sysmrngpxy.py
"""Morning COC direction from raw DTAF candles."""

import pandas as pd


def get_morning_direction():
    """Compare running close with mean(previous close, current open)."""
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    required = {"Open", "High", "Low", "Close"}
    if df is None or len(df) < 2 or not required.issubset(df.columns):
        return None, "NONE"

    raw = df.loc[:, ["Open", "High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce")
    if raw.iloc[-2:].isna().any().any():
        return None, "NONE"

    previous_close = raw["Close"].iloc[-2]
    current_close = raw["Close"].iloc[-1]
    current_open = raw["Open"].iloc[-1]
    reference = (previous_close + current_open) / 2.0
    direction = "UP" if current_close > reference else "DOWN" if current_close < reference else "NONE"
    return current_close, direction
