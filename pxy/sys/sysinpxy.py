"""PXY independent entry-signal channel (IN)."""

from datetime import datetime, time as dt_time

import pandas as pd

from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSINPXY_CANDLE_MODE,
    SYSDTHAPXY_INCLUDE_RUNNING_CANDLE,
    SYSSMAPXY_MA_PERIOD,
)
from sysdtafpxy import fetch_yf_data
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc
from syssmapxy import get_sma_signal
from sysstrnpxy import get_market_trend


def get_signal(df=None):
    """Return the configured IN state, including BULL/BEAR/SIDE in ST mode."""
    try:
        # IN must remain inactive through 09:17:00 IST.
        if datetime.now(SYSCNFGPXY_TIMEZONE).time() <= dt_time(9, 17):
            return "NONE"

        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        if SYSINPXY_CANDLE_MODE == "ST":
            evaluated_df = df
            if SYSDTHAPXY_INCLUDE_RUNNING_CANDLE != "YES":
                evaluated_df = evaluated_df.iloc[:-1]
            return get_market_trend(evaluated_df)

        transformed = transform_dtha_ohlc(df, mode=SYSINPXY_CANDLE_MODE)
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
    """Translate IN state into an execution action, with SMA50 confirming ST SIDE."""
    if SYSINPXY_CANDLE_MODE == "ST":
        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty:
            return "NONE"
        signal = get_signal(df)

        if signal == "SIDE":
            sma_df = df
            if (
                sma_df is not None
                and not sma_df.empty
                and SYSDTHAPXY_INCLUDE_RUNNING_CANDLE != "YES"
            ):
                sma_df = sma_df.iloc[:-1]
            sma = get_sma_signal(sma_df, period=SYSSMAPXY_MA_PERIOD)
            return {
                "BULL": "BUY",
                "BEAR": "SELL",
            }.get(str(sma.get("status", "NA")).upper(), "NONE")

        return {
            "BULL": "BUY",
            "BEAR": "SELL",
        }.get(signal, "NONE")

    signal = get_signal(df)
    return {
        "BULL": "BUY",
        "BEAR": "SELL",
        "BUY": "BUY",
        "SELL": "SELL",
    }.get(signal, "NONE")
