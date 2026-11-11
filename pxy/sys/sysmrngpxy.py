# sysmrngpxy.py
"""Morning-only direction from the centrally selected DTHA candles."""

import pandas as pd
from sysdthapxy import transform_dtha_ohlc


def get_morning_direction():
    """Compare the last two DTHA-transformed candle close values.

    Returns (latest_transformed_close, UP/DOWN/NONE). The input is never mutated.
    The running candle is included, matching the existing morning override.
    """
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is None or len(df) < 2 or not {"Open", "Close"}.issubset(df.columns):
        return None, "NONE"

    candles = transform_dtha_ohlc(df)
    if candles["Close"].iloc[-2:].isna().any():
        return None, "NONE"
    previous_close = candles["Close"].iloc[-2]
    current_close = candles["Close"].iloc[-1]
    direction = "UP" if current_close > previous_close else "DOWN" if current_close < previous_close else "NONE"
    return current_close, direction
