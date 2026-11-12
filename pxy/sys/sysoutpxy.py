"""PXY independent exit-signal channel (OUT)."""

import pandas as pd

from syscnfgpxy import (
    SYSOUTPXY_SIGNAL_MODE,
)
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc, get_stmt_states, get_supr_signals, get_stma_signals, get_pipe_binary_direction


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

        if SYSOUTPXY_SIGNAL_MODE == "PIPE":
            return get_pipe_binary_direction(df) or "NONE"

        if SYSOUTPXY_SIGNAL_MODE == "SUPR":
            return get_supr_signals(df)[1]

        if SYSOUTPXY_SIGNAL_MODE not in {"TSMAC0", "TSMAC1"}:
            return "NONE"

        transformed = get_out_candles(df)
        closes = pd.to_numeric(transformed["Close"], errors="coerce")

        # Compare the latest completed candle with the live running candle.
        # Candle direction is determined by transformed close vs previous close.
        if len(closes) < (2 if SYSOUTPXY_SIGNAL_MODE == "TSMAC0" else 3):
            return "NONE" if SYSOUTPXY_SIGNAL_MODE == "TSMAC0" else "SIDE"

        directions = get_close_direction_series(closes)
        if SYSOUTPXY_SIGNAL_MODE == "TSMAC0":
            return {"UP": "BULL", "DOWN": "BEAR"}.get(directions.iloc[-1], "NONE")
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
