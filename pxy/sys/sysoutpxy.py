"""PXY independent exit-signal channel (OUT)."""

import pandas as pd

from syscnfgpxy import (
    SYSDTHAPXY_CANDLE_MODE,
    SYSDTHAPXY_INCLUDE_RUNNING_CANDLE,
)
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc
from sysstrnpxy import get_market_trend


def get_out_candles(df):
    """Return the OHLC candles used by OUT, including its running-candle rule."""
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    transformed = transform_dtha_ohlc(df)
    if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE != "YES":
        transformed = transformed.iloc[:-1].copy()
    return transformed


def get_signal(df=None):
    """Return OUT direction; ST mode preserves BULL, BEAR, and SIDE."""
    try:
        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        transformed = get_out_candles(df)
        if SYSDTHAPXY_CANDLE_MODE == "ST":
            return get_market_trend(transformed)

        closes = pd.to_numeric(transformed["Close"], errors="coerce")

        # Require C0, C1, and C2 so the C1/C0 candle colours are both defined.
        if len(closes) < 3:
            return "NONE"

        directions = get_close_direction_series(closes)
        c1_direction = directions.iloc[-2]
        c0_direction = directions.iloc[-1]
        if c1_direction not in {"UP", "DOWN"} or c0_direction not in {"UP", "DOWN"}:
            return "NONE"

        if c0_direction == "UP":
            return "BULL"
        if c0_direction == "DOWN":
            return "BEAR"
        return "NONE"
    except Exception:
        return "NONE"


if __name__ == "__main__":
    print(f"OUT SIGNAL: {get_signal()}")
