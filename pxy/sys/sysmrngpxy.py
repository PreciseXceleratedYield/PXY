# sysmrngpxy.py
"""Morning-only OC2 direction from raw DTAF candles (independent of DTHA)."""

import pandas as pd


def get_morning_direction():
    """Transform raw DTAF OHLC into OC2 candles and compare the last two closes.

    OC2 close is the midpoint of raw Open and Close. The source frame is never mutated.
    The running candle is included, matching the existing morning override.
    """
    from sysdtafpxy import fetch_yf_data
    df = fetch_yf_data()
    required = {"Open", "High", "Low", "Close"}
    if df is None or len(df) < 2 or not required.issubset(df.columns):
        return None, "NONE"

    raw = df.loc[:, ["Open", "High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce")
    if raw.iloc[-2:].isna().any().any():
        return None, "NONE"

    oc2_close = (raw["Open"] + raw["Close"]) / 2.0
    previous_close = oc2_close.iloc[-2]
    current_close = oc2_close.iloc[-1]
    direction = "UP" if current_close > previous_close else "DOWN" if current_close < previous_close else "NONE"
    return current_close, direction
