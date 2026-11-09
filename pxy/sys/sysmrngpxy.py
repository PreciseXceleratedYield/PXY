# sysmrngpxy.py
"""Morning-only OC/2 candle direction, independent of configured DTHA mode."""

import pandas as pd

from sysdirpxy import detect_raw_direction


def get_morning_direction(df=None):
    """Compare the last two (Open + Close)/2 candle values.

    Returns (latest_transformed_close, UP/DOWN/NONE). The input is never mutated.
    The running candle is included, matching the existing morning override.
    """
    if df is None:
        from sysdtafpxy import fetch_yf_data
        df = fetch_yf_data()
    if df is None or len(df) < 2 or not {"Open", "Close"}.issubset(df.columns):
        return None, "NONE"

    candles = df.copy()
    opens = pd.to_numeric(candles["Open"], errors="coerce")
    closes = pd.to_numeric(candles["Close"], errors="coerce")
    candles["Close"] = (opens + closes) / 2.0
    if candles["Close"].iloc[-2:].isna().any():
        return None, "NONE"
    return detect_raw_direction(candles)
