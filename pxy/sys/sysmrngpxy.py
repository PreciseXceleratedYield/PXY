# sysmrngpxy.py
"""Morning-only PIPE direction from raw DTAF candles (independent of DTHA)."""

import pandas as pd


def get_morning_direction():
    """Transform raw DTAF OHLC into PIPE candles and compare the last two closes.

    PIPE uses the full candle range with no wicks: bullish candles close at
    High, bearish candles close at Low. The source frame is never mutated.
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

    bullish = raw["Close"] >= raw["Open"]
    pipe_close = raw["High"].where(bullish, raw["Low"])
    previous_close = pipe_close.iloc[-2]
    current_close = pipe_close.iloc[-1]
    direction = "UP" if current_close > previous_close else "DOWN" if current_close < previous_close else "NONE"
    return current_close, direction
