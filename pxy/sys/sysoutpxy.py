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

        # OUT follows the current live candle's direction versus the previous close.
        # A reversal takes effect immediately; no two-candle confirmation.
        if len(closes) < 2:
            return "NONE"

        current_direction = get_close_direction_series(closes).iloc[-1]
        if current_direction == "UP":
            return "BULL"
        if current_direction == "DOWN":
            return "BEAR"
        return "NONE"
    except Exception:
        return "NONE"


if __name__ == "__main__":
    print(f"OUT SIGNAL: {get_signal()}")
