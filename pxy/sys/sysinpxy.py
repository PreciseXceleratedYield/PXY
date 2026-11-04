"""PXY independent entry-signal channel (IN)."""

from datetime import datetime, time as dt_time

import pandas as pd

from syscnfgpxy import (
    SYSCNFGPXY_TIMEZONE,
    SYSCNFGPXY_ENTRY_CUTOFF,
    SYSINPXY_CONFIRM_MODE,
    SYSINPXY_SIGNAL_MODE,
)
from sysdtafpxy import fetch_yf_data
from sysexitpxy import detect_raw_direction
from sysdthapxy import get_close_direction_series, transform_dtha_ohlc, get_stmt_states


def get_signal(df=None):
    """Return the pure DTHA IN state."""
    try:
        # IN must remain inactive through 09:17:00 IST.
        now_time = datetime.now(SYSCNFGPXY_TIMEZONE).time()
        if now_time <= dt_time(9, 17) or now_time >= SYSCNFGPXY_ENTRY_CUTOFF:
            return "NONE"

        if df is None:
            df = fetch_yf_data()
        if df is None or df.empty or "Close" not in df.columns:
            return "NONE"

        # Live mode: include the forming candle in entry signals.

        if SYSINPXY_SIGNAL_MODE == "STMT":
            states = get_stmt_states(df)
            if states.empty:
                return "NONE"
            current = states.iloc[-1]
            if current == "BULL":
                return "BUY"
            if current == "BEAR":
                return "SELL"
            if current == "SIDE":
                # Contrarian Mullu entry only when STMT is SIDE.
                _, raw_direction = detect_raw_direction(df)
                return {"UP": "SELL", "DOWN": "BUY"}.get(raw_direction, "NONE")
            return "NONE"

        transformed = transform_dtha_ohlc(df)
        closes = pd.to_numeric(transformed["Close"], errors="coerce")
        # Confirm a completed-candle flip with the live running candle.
        # C2 and C1 are completed candles; C0 is the forming candle.
        if len(closes) < 4:
            return "NONE"

        directions = get_close_direction_series(closes)
        past_completed = directions.iloc[-3]
        latest_completed = directions.iloc[-2]
        running = directions.iloc[-1]

        if (past_completed, latest_completed, running) == ("DOWN", "UP", "UP"):
            return "BUY"
        if (past_completed, latest_completed, running) == ("UP", "DOWN", "DOWN"):
            return "SELL"
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
