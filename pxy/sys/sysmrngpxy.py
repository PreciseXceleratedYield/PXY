# sysmrngpxy.py
"""Morning RAW0 direction from the current raw DTAF candle."""

import pandas as pd


def get_morning_direction():
    """Compare running raw close with current raw open (RAW0)."""
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    required = {"Open", "High", "Low", "Close"}
    if df is None or len(df) < 2 or not required.issubset(df.columns):
        return None, "NONE"

    raw = df.loc[:, ["Open", "High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce")
    if raw.iloc[-2:].isna().any().any():
        return None, "NONE"

    current_close = raw["Close"].iloc[-1]
    current_open = raw["Open"].iloc[-1]
    reference = current_open
    direction = "UP" if current_close > reference else "DOWN" if current_close < reference else "NONE"
    return current_close, direction
