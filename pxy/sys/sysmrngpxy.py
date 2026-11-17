# sysmrngpxy.py
"""Morning-only direction from raw DTAF closes (independent of DTHA)."""

import pandas as pd


def get_morning_direction():
    """Compare the last two actual raw closes, including the running candle."""
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
    direction = "UP" if current_close > previous_close else "DOWN" if current_close < previous_close else "NONE"
    return current_close, direction
