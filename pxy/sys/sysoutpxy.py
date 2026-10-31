"""PXY independent exit-signal channel (OUT)."""

import pandas as pd

from syscnfgpxy import (
    SYSOUTPXY_CANDLE_MODE,
    SYSDTHAPXY_INCLUDE_RUNNING_CANDLE,
)
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc


def get_signal(df=None):
    """Return only the latest direction: BULL, BEAR, or NONE."""
    try:
        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        transformed = transform_dtha_ohlc(df, mode=SYSOUTPXY_CANDLE_MODE)
        closes = pd.to_numeric(transformed["Close"], errors="coerce")
        if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE != "YES":
            closes = closes.iloc[:-1]

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
