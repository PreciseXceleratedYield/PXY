"""PXY independent entry-signal channel (IN)."""

from datetime import datetime, time as dt_time

import pandas as pd

from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSDTHAPXY_INCLUDE_RUNNING_CANDLE,
)
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc


def get_signal(df=None):
    """Return the pure DTHA IN state."""
    try:
        # IN must remain inactive through 09:17:00 IST.
        if datetime.now(SYSCNFGPXY_TIMEZONE).time() <= dt_time(9, 17):
            return "NONE"

        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        transformed = transform_dtha_ohlc(df)
        closes = pd.to_numeric(transformed["Close"], errors="coerce")
        if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE != "YES":
            closes = closes.iloc[:-1]

        # C0 needs C1, and C1 needs C2, to establish both candle colours.
        if len(closes) < 3:
            return "NONE"

        directions = get_close_direction_series(closes)
        c1_direction = directions.iloc[-2]
        c0_direction = directions.iloc[-1]
        if c1_direction not in {"UP", "DOWN"} or c0_direction not in {"UP", "DOWN"}:
            return "NONE"

        if c1_direction == "UP" and c0_direction == "UP":
            return "BULL"
        if c1_direction == "DOWN" and c0_direction == "DOWN":
            return "BEAR"
        if c1_direction == "UP" and c0_direction == "DOWN":
            return "SELL"
        if c1_direction == "DOWN" and c0_direction == "UP":
            return "BUY"
        return "NONE"
    except Exception:
        return "NONE"


if __name__ == "__main__":
    print(f"IN SIGNAL: {get_signal()}")

def get_entry_signal(df=None):
    """Translate pure IN state into BUY, SELL, or NONE."""
    signal = get_signal(df)
    return {
        "BUY": "BUY",
        "SELL": "SELL",
    }.get(signal, "NONE")
