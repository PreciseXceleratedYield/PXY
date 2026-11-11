# sysmrngpxy.py
"""Morning-only direction from raw DTAF candles (independent of DTHA)."""

import pandas as pd


def get_morning_direction():
    """Compare the last two raw DTAF candle close values.

    Returns (latest_raw_close, UP/DOWN/NONE). The input is never mutated.
    The running candle is included, matching the existing morning override.
    """
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is None or len(df) < 2 or not {"Open", "Close"}.issubset(df.columns):
        return None, "NONE"

    candles = df
    if candles["Close"].iloc[-2:].isna().any():
        return None, "NONE"
    previous_close = candles["Close"].iloc[-2]
    current_close = candles["Close"].iloc[-1]
    direction = "UP" if current_close > previous_close else "DOWN" if current_close < previous_close else "NONE"
    return current_close, direction
