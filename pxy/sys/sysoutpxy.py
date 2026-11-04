"""PXY independent exit-signal channel (OUT)."""

import pandas as pd

from syscnfgpxy import (
    SYSOUTPXY_SIGNAL_MODE,
)
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc, get_stmt_states


def get_out_candles(df):
    """Return the OHLC candles used by OUT, including its running-candle rule."""
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    transformed = transform_dtha_ohlc(df)
    # Always include the running candle for live OUT signals.
    return transformed


def get_signal(df=None):
    """Return pure DTHA OUT direction."""
    try:
        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        if SYSOUTPXY_SIGNAL_MODE == "STMT":
            states = get_stmt_states(df)
            return str(states.iloc[-1]) if not states.empty else "NONE"

        transformed = get_out_candles(df)
        closes = pd.to_numeric(transformed["Close"], errors="coerce")

        # Require C0, C1, and C2 so the C1/C0 candle colours are both defined.
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
        return "NONE"
    except Exception:
        return "NONE"


if __name__ == "__main__":
    print(f"OUT SIGNAL: {get_signal()}")
