# sysmrngpxy.py
"""Morning-only OCC3 candle direction, independent of configured DTHA mode."""

import pandas as pd


def get_morning_direction():
    """Compare the last two (Open + 2*Close)/3 candle values.

    Returns (latest_transformed_close, UP/DOWN/NONE). The input is never mutated.
    The running candle is included, matching the existing morning override.
    """
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    if df is None or len(df) < 2 or not {"Open", "Close"}.issubset(df.columns):
        return None, "NONE"

    candles = df.copy()
    opens = pd.to_numeric(candles["Open"], errors="coerce")
    closes = pd.to_numeric(candles["Close"], errors="coerce")
    candles["Close"] = (opens + 2.0 * closes) / 3.0
    if candles["Close"].iloc[-2:].isna().any():
        return None, "NONE"
    previous_close = candles["Close"].iloc[-2]
    current_close = candles["Close"].iloc[-1]
    direction = "UP" if current_close > previous_close else "DOWN" if current_close < previous_close else "NONE"
    return current_close, direction
