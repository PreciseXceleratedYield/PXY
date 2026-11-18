# sysmrngpxy.py
"""Morning RAW0 direction from the shared DTHA candle stream."""

import pandas as pd


def get_morning_direction(df=None):
    """Compare the running DTHA close with its open (morning DTHA mode: RAW)."""
    from sysdtafpxy import fetch_yf_data
    from sysdthapxy import transform_dtha_ohlc
    if df is None:
        df = fetch_yf_data()
    required = {"Open", "High", "Low", "Close"}
    if df is None or len(df) < 2 or not required.issubset(df.columns):
        return None, "NONE"

    candles = transform_dtha_ohlc(df)
    candles = candles.loc[:, ["Open", "High", "Low", "Close"]].apply(pd.to_numeric, errors="coerce")
    if candles.iloc[-2:].isna().any().any():
        return None, "NONE"

    current_close = candles["Close"].iloc[-1]
    current_open = candles["Open"].iloc[-1]
    reference = current_open
    direction = "UP" if current_close > reference else "DOWN" if current_close < reference else "NONE"
    return current_close, direction
