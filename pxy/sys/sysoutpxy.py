"""PXY independent exit-signal channel (OUT)."""

import pandas as pd

from syscnfgpxy import (
    SYSOUTPXY_SIGNAL_MODE,
)
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc, get_stmt_states, get_strw_signals, get_stma_signals


def get_out_candles(df):
    """Return the OHLC candles used by OUT, including its running-candle rule."""
    if df is None or df.empty:
        return df.copy() if df is not None else pd.DataFrame()

    transformed = transform_dtha_ohlc(df)
    # Live mode: include the forming candle in OUT.
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

        if SYSOUTPXY_SIGNAL_MODE == "STRW":
            return get_strw_signals(df)[1]

        if SYSOUTPXY_SIGNAL_MODE != "TSMA":
            return "NONE"

        transformed = get_out_candles(df)
        closes = pd.to_numeric(transformed["Close"], errors="coerce")

        # Compare the latest completed candle with the live running candle.
        # Candle direction is determined by transformed close vs previous close.
        if len(closes) < 3:
            return "SIDE"

        directions = get_close_direction_series(closes)
        completed_direction = directions.iloc[-2]
        running_direction = directions.iloc[-1]
        if completed_direction == "UP" and running_direction == "UP":
            return "BULL"
        if completed_direction == "DOWN" and running_direction == "DOWN":
            return "BEAR"
        return "SIDE"
    except Exception:
        return "NONE"


if __name__ == "__main__":
    print(f"OUT SIGNAL: {get_signal()}")
